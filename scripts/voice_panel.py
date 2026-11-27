"""Lightweight Qt map, microphone control and live ROS command/status viewer."""
import json
import math
import os
import signal
from pathlib import Path
import sys
import time

import cv2
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets
import rclpy
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions
from geometry_msgs.msg import PoseWithCovarianceStamped, Twist
from nav_msgs.msg import Path as NavPath, Odometry
from sensor_msgs.msg import LaserScan
from rosgraph_msgs.msg import Clock
from rcl_interfaces.msg import Log
from irobot_create_msgs.msg import HazardDetectionVector, HazardDetection
from tf2_msgs.msg import TFMessage
from tf2_ros import Buffer, TransformListener, TransformException
from lifecycle_msgs.srv import GetState
from std_msgs.msg import String
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
from map_utils import GridMap
from audio_devices import inputs
from generate_demo_map import DOCK

ROOT = Path(__file__).resolve().parents[1]
COLORS = ['#5cbd91', '#619de3', '#e6b64f']
STATES = {'READY': 'Sẵn sàng nhận lệnh', 'ACCEPTED': 'Đã nhận tuyến', 'PROGRESS': 'Đang di chuyển',
          'PLANNING': 'Đang tính đường toàn tuyến', 'PLAN_READY': 'Đã lập đường toàn tuyến',
          'GOAL_SENT': 'Đang di chuyển', 'COMPLETED': 'Đã đến nơi — hoàn tất',
          'FAILED': 'Điều hướng thất bại', 'INVALID': 'Lệnh không hợp lệ',
          'NOT_READY': 'Nav2 chưa sẵn sàng — hãy initialize', 'BUSY': 'Robot đang thực hiện tuyến trước',
          'CANCELED': 'Đã hủy điều hướng', 'CANCEL_ACK': 'Đang hủy lệnh',
          'CANCEL_REQUESTED': 'Đã yêu cầu dừng', 'IDLE': 'Robot đang nghỉ'}


class MapView(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.grid = GridMap(ROOT/'maps/map.yaml')
        self.regions = json.loads((ROOT/'config/regions.json').read_text())['regions']
        rgb = cv2.cvtColor(self.grid.image, cv2.COLOR_GRAY2RGB)
        labels = np.load(ROOT/'config/region_labels.npy')
        for i, color in enumerate(COLORS, 1):
            c = QtGui.QColor(color)
            mask = labels == i
            rgb[mask] = (.55*rgb[mask] + .45*np.array([c.red(), c.green(), c.blue()])).astype(np.uint8)
        h,w,_ = rgb.shape
        self.image = QtGui.QImage(rgb.data,w,h,3*w,QtGui.QImage.Format_RGB888).copy()
        self.robot = None
        self.ground_truth = None
        self.scan_points = []
        self.path = []
        self.preview = []
        self.route = []
        self.completed = 0
        self.active = None
        self.setMinimumSize(580, 430)

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.fillRect(self.rect(), QtGui.QColor('#edf2f5'))
        scale = min((self.width()-24)/self.grid.w, (self.height()-24)/self.grid.h)
        left = (self.width()-self.grid.w*scale)/2
        top = (self.height()-self.grid.h*scale)/2
        p.drawImage(QtCore.QRectF(left,top,self.grid.w*scale,self.grid.h*scale),self.image)

        def point(x,y):
            col = (x-self.grid.ox)/self.grid.res
            row = self.grid.h-(y-self.grid.oy)/self.grid.res
            return QtCore.QPointF(left+col*scale,top+row*scale)
        p.setPen(QtGui.QColor('#9a5913'))
        p.setFont(QtGui.QFont('DejaVu Sans',9))
        p.drawText(point(DOCK[0]+.15,DOCK[1]+.15),'Dock')
        if self.preview:
            p.setPen(QtGui.QPen(QtGui.QColor('#a64ac9'),3,QtCore.Qt.DashLine))
            p.drawPolyline(QtGui.QPolygonF([point(x,y) for x,y in self.preview]))
        if self.path:
            p.setPen(QtGui.QPen(QtGui.QColor('#1469d5'),3))
            p.drawPolyline(QtGui.QPolygonF([point(x,y) for x,y in self.path]))
        p.setPen(QtGui.QPen(QtGui.QColor('#df4c4c'),3))
        p.drawPoints(QtGui.QPolygonF([point(x,y) for x,y in self.scan_points]))
        if self.ground_truth:
            at=point(*self.ground_truth[:2])
            p.setBrush(QtCore.Qt.NoBrush)
            p.setPen(QtGui.QPen(QtGui.QColor('#d27c16'),2,QtCore.Qt.DashLine))
            p.drawEllipse(at,13,13)
        for i,r in enumerate(self.regions):
            at=point(r['goal']['x'], r['goal']['y'])
            color=QtGui.QColor(COLORS[i%3])
            p.setPen(QtGui.QPen(QtGui.QColor('#16314b'), 3 if self.active==r['id'] else 1))
            p.setBrush(color)
            p.drawEllipse(at,7,7)
            box=QtCore.QRectF(at.x()-23,at.y()-52,46,36)
            p.setBrush(QtGui.QColor('#ffffff'))
            p.setPen(QtGui.QPen(color,2))
            p.drawRoundedRect(box,8,8)
            p.setPen(QtGui.QColor('#19314a'))
            p.setFont(QtGui.QFont('DejaVu Sans',16,QtGui.QFont.Bold))
            p.drawText(box,QtCore.Qt.AlignCenter,r['id'])
            order=[str(i+1) for i,region in enumerate(self.route) if region==r['id']]
            if order:
                badge=QtCore.QRectF(at.x()+26,at.y()-51,max(24,15*len(','.join(order))),24)
                p.setBrush(QtGui.QColor('#e6dbef'))
                p.setPen(QtGui.QColor('#80339e'))
                p.drawRoundedRect(badge,5,5)
                p.setFont(QtGui.QFont('DejaVu Sans',10,QtGui.QFont.Bold))
                p.drawText(badge,QtCore.Qt.AlignCenter,','.join(order))
        if self.robot:
            x,y,yaw=self.robot
            at=point(x,y)
            p.setBrush(QtGui.QColor('#152d47'))
            p.setPen(QtGui.QPen(QtGui.QColor('white'),2))
            p.drawEllipse(at,10,10)
            p.setPen(QtGui.QPen(QtGui.QColor('#e85b53'),3))
            p.drawLine(at,at+QtCore.QPointF(22*math.cos(yaw),-22*math.sin(yaw)))
        p.end()


class Panel(QtWidgets.QWidget):
    def __init__(self,node):
        super().__init__()
        self.node=node
        self.setWindowTitle('Điều hướng giọng nói · A / B / C')
        self.resize(1120,720)
        self.setStyleSheet('QWidget {font-family: DejaVu Sans; font-size: 12px;} '
            'QPushButton {padding: 10px; border-radius: 6px; background: #e2eaf3;} '
            'QPushButton:disabled {color: #999;} QLineEdit,QComboBox {padding: 7px;}')
        root=QtWidgets.QVBoxLayout(self)
        title=QtWidgets.QLabel('BẢN ĐỒ PHÒNG · ĐIỀU HƯỚNG GIỌNG NÓI')
        title.setStyleSheet('font-size: 19px; font-weight: bold; color: #19314a; padding: 8px;')
        root.addWidget(title)
        body=QtWidgets.QHBoxLayout()
        root.addLayout(body,1)
        self.map=MapView()
        body.addWidget(self.map,3)
        side=QtWidgets.QVBoxLayout()
        body.addLayout(side,2)
        self.readiness=QtWidgets.QLabel('Đang chờ AMCL / Nav2…')
        side.addWidget(self.readiness)
        self.heard=QtWidgets.QLabel('Bạn nói: —')
        self.heard.setWordWrap(True)
        self.heard.setStyleSheet('font-size: 17px; background: #eaf3ff; padding: 14px; border-radius: 8px;')
        side.addWidget(self.heard)
        self.status=QtWidgets.QLabel('Chờ khởi tạo robot (initialize)')
        self.status.setWordWrap(True)
        self.status.setStyleSheet('font-size: 15px; padding: 12px; color: #225c44;')
        side.addWidget(self.status)
        self.route=QtWidgets.QLabel('Tuyến: —')
        side.addWidget(self.route)
        self.diagnostics=QtWidgets.QLabel('Đang đọc vận tốc, LiDAR và phản hồi robot…')
        self.diagnostics.setWordWrap(True)
        self.diagnostics.setStyleSheet('padding: 8px; background: #fff3d8; border-radius: 6px;')
        side.addWidget(self.diagnostics)
        self.devices=QtWidgets.QComboBox()
        self.devices.addItem('Tự chọn micro USB / micro số laptop',None)
        try:
            for i,name in inputs():
                self.devices.addItem(f'{i}: {name}',i)
        except Exception as error:
            self.status.setText(f'Không đọc được micro: {error}')
        side.addWidget(self.devices)
        self.mic=QtWidgets.QPushButton('●  Thu một câu (6 giây)')
        self.mic.setStyleSheet('background: #216b50; color: white; padding: 12px; font-weight: bold;')
        self.mic.clicked.connect(self.record)
        side.addWidget(self.mic)
        self.audio=QtWidgets.QLabel('Micro: chưa thu. Bấm nút rồi nói khi hiện “Đang thu”.')
        self.audio.setWordWrap(True)
        side.addWidget(self.audio)
        stop=QtWidgets.QPushButton('■  Dừng robot / hủy tuyến')
        stop.clicked.connect(lambda:self.send('Dừng lại'))
        side.addWidget(stop)
        self.input=QtWidgets.QLineEdit()
        self.input.setPlaceholderText('Thử bằng văn bản: Đi đến khu vực A')
        self.input.returnPressed.connect(self.send_text)
        side.addWidget(self.input)
        send=QtWidgets.QPushButton('Gửi văn bản thử nghiệm')
        send.clicked.connect(self.send_text)
        side.addWidget(send)
        examples=QtWidgets.QLabel('Ví dụ: “Đi từ phòng A qua hành lang C rồi đến phòng B.”\n“Đi đến A rồi đến B.”')
        examples.setWordWrap(True)
        side.addWidget(examples)
        self.history=QtWidgets.QPlainTextEdit()
        self.history.setReadOnly(True)
        self.history.setMaximumBlockCount(80)
        side.addWidget(self.history,1)
        footer=QtWidgets.QLabel('A/B: Phòng · C: Hành lang · Đỏ: LiDAR · Xanh: chặng hiện tại · Tím nét đứt: toàn tuyến dự kiến · Ô số: thứ tự ghé')
        root.addWidget(footer)
        self.publisher=node.create_publisher(String,'/voice_command',10)
        node.create_subscription(String,'/voice_command',self.command,10)
        qos=QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL)
        node.create_subscription(String,'/voice_navigation/status',self.navigation_event,qos)
        node.create_subscription(String,'/speech_recognition/status',self.asr,10)
        node.create_subscription(PoseWithCovarianceStamped,'/amcl_pose',self.pose,qos)
        node.create_subscription(NavPath,'/plan',self.plan,10)
        node.create_subscription(NavPath,'/voice_navigation/preview_path',self.preview,qos)
        sensor_qos=QoSProfile(depth=1,reliability=ReliabilityPolicy.BEST_EFFORT)
        self.tf=Buffer(node=node)
        self.tf_listener=TransformListener(self.tf,node)
        self.commanded=(0.,0.)
        self.measured=(0.,0.)
        self.hazards=[]
        self.scan=None
        self.front=None
        self.warning=('',0.)
        self.clock_last=None
        self.sim_rate=None
        self.motion_since=time.monotonic()
        self.odom_at=0.
        self.scan_at=0.
        node.create_subscription(Twist,'/cmd_vel',self.velocity,10)
        node.create_subscription(Odometry,'/odom',self.odometry,sensor_qos)
        node.create_subscription(LaserScan,'/scan',self.laser,sensor_qos)
        node.create_subscription(HazardDetectionVector,'/hazard_detection',lambda m:setattr(self,'hazards',[d.type for d in m.detections]),sensor_qos)
        node.create_subscription(Clock,'/clock',self.clock,sensor_qos)
        node.create_subscription(TFMessage,'/_internal/sim_ground_truth_pose',self.ground_truth,sensor_qos)
        node.create_subscription(Log,'/rosout',self.robot_log,10)
        self.process=None
        self.robot_ready=False
        self.mic.setEnabled(False)
        self.health_client=node.create_client(GetState,'/bt_navigator/get_state')
        self.health_future=None
        self.health_at=0.
        self.timer=QtCore.QTimer(self)
        self.timer.timeout.connect(self.spin)
        self.timer.start(100)

    def spin(self):
        if not rclpy.ok():
            self.close()
            QtWidgets.QApplication.quit()
            return
        spin_start=time.monotonic()
        for _ in range(50):
            rclpy.spin_once(self.node,timeout_sec=0)
            if time.monotonic()-spin_start>.01:
                break
        self.update_motion()
        now=time.monotonic()
        if now-self.health_at>3.:
            self.health_at=now
            if self.health_future and not self.health_future.done():
                self.health_client.remove_pending_request(self.health_future)
                self.health_future.cancel()
            if self.health_client.service_is_ready():
                self.health_future=self.health_client.call_async(GetState.Request())
                self.health_future.add_done_callback(self.health)
            else:
                self.robot_ready=False
                self.mic.setEnabled(False)
                self.readiness.setText('Mô phỏng / Nav2 chưa mở hoặc đã dừng')
        self.map.update()

    def health(self,future):
        if future.cancelled() or future.exception():
            return
        active=future.result().current_state.label=='active'
        try:
            initialized=json.loads((ROOT/'.runtime/initialization.json').read_text()).get('state')=='READY'
        except (OSError,ValueError):
            initialized=False
        self.robot_ready=bool(active and self.map.robot and initialized)
        self.readiness.setText('● Nav2 active · robot đã định vị, undock xong' if self.robot_ready else 'Đang khởi tạo AMCL / Nav2 và undock…')
        self.mic.setEnabled(self.robot_ready and (not self.process or self.process.state()==QtCore.QProcess.NotRunning))

    def send(self,text):
        self.publisher.publish(String(data=text))

    def send_text(self):
        if not self.robot_ready:
            self.status.setText('Đợi robot khởi tạo và undock xong trước khi gửi tuyến.')
            return
        if self.input.text().strip():
            self.send(self.input.text().strip())
            self.input.clear()

    def command(self,msg):
        self.heard.setText(f'Bạn nói / lệnh nhận được:\n{msg.data}')

    def navigation_event(self,msg):
        e=json.loads(msg.data)
        state=e['state']
        if e.get('command'):
            self.heard.setText('Bạn nói / lệnh nhận được:\n'+e['command'])
        text=STATES.get(state,state)
        if e.get('region'):
            text+=f" · khu vực {e['region']}"
        if state=='PROGRESS':
            text+=f"\nCòn {e['distance_remaining']:.2f} m · phục hồi {e['recoveries']} lần"
        if e.get('step') and e.get('route'):
            text+=f" · chặng {e['step']}/{len(e['route'])}"
        if e.get('reason') and state!='READY':
            text+='\n'+e['reason']
        self.status.setText(text)
        if state!='PROGRESS':
            self.history.appendPlainText(text)
        if e.get('route'):
            self.map.route=e['route']
            self.map.completed=len(e.get('completed',[]))
            step=e.get('step',0)
            order=[]
            for i,region in enumerate(e['route'],1):
                symbol='✓' if i<=self.map.completed else ('▶' if i==step and state not in ('FAILED','CANCELED','COMPLETED','IDLE') else '○')
                order.append(f'{symbol} {i}:{region}')
            self.route.setText('Tuyến: '+' → '.join(order))
        if state in ('GOAL_SENT','PROGRESS'):
            self.map.active=e['region']
        if state in ('COMPLETED','FAILED','CANCELED'):
            self.map.active=None
            self.map.path=[]
            self.map.preview=[]

    def asr(self,msg):
        e=json.loads(msg.data)
        self.audio.setText(e.get('message',e.get('state','')))
        if 'text' in e:
            self.heard.setText('Bạn nói:\n'+(e['text'] or '(Chưa nhận được tiếng nói)'))
        if 'rms_db' in e:
            self.audio.setText(self.audio.text()+f"\nMức thu: {e['rms_db']:.0f} dBFS · peak {e['peak']:.3f}")

    def pose(self,msg):
        pose=msg.pose.pose
        q=pose.orientation
        yaw=math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))
        self.map.robot=(pose.position.x,pose.position.y,yaw)

    def plan(self,msg):
        if self.map.active:
            self.map.path=[(p.pose.position.x,p.pose.position.y) for p in msg.poses]

    def preview(self,msg):
        self.map.preview=[(p.pose.position.x,p.pose.position.y) for p in msg.poses]

    def velocity(self,msg):
        self.commanded=(msg.linear.x,msg.angular.z)

    def odometry(self,msg):
        self.odom_at=time.monotonic()
        self.measured=(msg.twist.twist.linear.x,msg.twist.twist.angular.z)
        if abs(self.measured[0])>.01 or abs(self.measured[1])>.04:
            self.motion_since=time.monotonic()

    def clock(self,msg):
        now=time.monotonic()
        sim=msg.clock.sec+msg.clock.nanosec/1e9
        if self.clock_last and now-self.clock_last[0]>.5:
            self.sim_rate=max(0.,(sim-self.clock_last[1])/(now-self.clock_last[0]))
            self.clock_last=(now,sim)
        elif self.clock_last is None:
            self.clock_last=(now,sim)

    def laser(self,msg):
        self.scan=msg
        self.scan_at=time.monotonic()

    def ground_truth(self,msg):
        for t in msg.transforms:
            if t.child_frame_id=='turtlebot4' and t.header.frame_id=='rooms':
                v=t.transform.translation
                self.map.ground_truth=(v.x,v.y)

    def robot_log(self,msg):
        if msg.level>=30 and msg.name in ('motion_control','controller_server','bt_navigator','planner_server'):
            reason=msg.msg
            if 'autonomous behavior' in reason:
                reason='Create 3 đang chạy hành vi riêng, tạm chặn vận tốc Nav2'
            elif 'backup limit' in reason:
                reason='Create 3 chặn lùi vì đã chạm giới hạn lùi'
            elif 'progress' in reason.lower():
                reason='Nav2 không thấy robot tiến triển, đang thử phục hồi'
            self.warning=(reason,time.monotonic())

    def update_motion(self):
        try:
            t=self.tf.lookup_transform('map','base_link',rclpy.time.Time()).transform
            q=t.rotation
            self.map.robot=(t.translation.x,t.translation.y,math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z)))
            if self.scan:
                scan=self.scan
                t=self.tf.lookup_transform('map',scan.header.frame_id,rclpy.time.Time.from_msg(scan.header.stamp)).transform
                q=t.rotation
                yaw=math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))
                angles=scan.angle_min+np.arange(len(scan.ranges))*scan.angle_increment
                bearings=angles+yaw-self.map.robot[2]
                bearings=np.arctan2(np.sin(bearings),np.cos(bearings))
                ranges=np.asarray(scan.ranges)
                valid=(np.abs(bearings)<math.pi/6)&np.isfinite(ranges)&(ranges>=scan.range_min)&(ranges<=scan.range_max)
                self.front=float(ranges[valid].min()) if valid.any() else None
                self.map.scan_points=[(t.translation.x+r*math.cos(yaw+scan.angle_min+i*scan.angle_increment),
                                      t.translation.y+r*math.sin(yaw+scan.angle_min+i*scan.angle_increment))
                                     for i,r in enumerate(scan.ranges) if i%4==0 and math.isfinite(r) and scan.range_min<=r<=scan.range_max]
        except TransformException:
            self.map.scan_points=[]
        v,w=self.measured
        requested=self.commanded
        lines=[f'Vận tốc: yêu cầu {requested[0]:.2f} · odom {v:.2f} m/s',f'Quay: yêu cầu {requested[1]:.2f} · odom {w:.2f} rad/s']
        if time.monotonic()-self.odom_at>2:
            lines.append('Chưa nhận odometry mới — chưa biết robot có chuyển động không')
        if time.monotonic()-self.scan_at>2:
            lines.append('Chưa nhận LiDAR mới')
            self.map.scan_points=[]
        if self.front is not None:
            lines.append(f'LiDAR phía trước: {self.front:.2f} m')
        if self.sim_rate is not None:
            lines.append(f'Tốc độ mô phỏng: {self.sim_rate:.2f}× thời gian thực')
        if self.clock_last and time.monotonic()-self.clock_last[0]>3:
            lines.append('Clock không cập nhật — mô phỏng có thể đã tạm dừng')
        if self.map.robot and self.map.ground_truth:
            error=math.dist(self.map.robot[:2],self.map.ground_truth)
            lines.append(f'Lệch ước lượng / Gazebo: {error:.2f} m')
            if error>.4:
                lines.append('Định vị đang lệch: so sánh chấm đen với vòng cam')
        names={HazardDetection.BUMP:'va chạm bumper',HazardDetection.CLIFF:'cảm biến vực',HazardDetection.STALL:'kẹt bánh',HazardDetection.WHEEL_DROP:'bánh bị nhấc'}
        hazards=[names[h] for h in self.hazards if h in names]
        if hazards:
            lines.append('Cảnh báo: '+', '.join(hazards))
        if time.monotonic()-self.warning[1]<10:
            lines.append(self.warning[0])
        if time.monotonic()-self.odom_at<2 and time.monotonic()-self.motion_since>4 and (abs(requested[0])>.03 or abs(requested[1])>.1):
            lines.append('Đang có lệnh vận tốc nhưng robot chưa chuyển động')
        if self.node.count_publishers('/clock')>1:
            lines.append('LỖI: có nhiều mô phỏng cùng phát clock — dừng demo chạy trùng')
        self.diagnostics.setText('\n'.join(lines))

    def record(self):
        self.mic.setEnabled(False)
        self.audio.setText('Đang nạp model small đã có. Chờ thông báo “Đang thu” rồi nói.')
        self.process=QtCore.QProcess(self)
        args=[str(ROOT/'scripts/speech_recognition.py'),'--model','small','--once']
        if self.devices.currentData() is not None:
            args+=['--device',str(self.devices.currentData())]
        self.process.setProcessChannelMode(QtCore.QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.read_output)
        self.process.finished.connect(self.finished)
        self.process.errorOccurred.connect(lambda _:self.audio.setText('Không khởi động được nhận dạng.'))
        self.process.start(sys.executable,args)

    def read_output(self):
        text=bytes(self.process.readAllStandardOutput()).decode(errors='replace').strip()
        for line in text.splitlines():
            try:
                event=json.loads(line)
                self.history.appendPlainText(event.get('message',line))
            except ValueError:
                self.history.appendPlainText(line)

    def finished(self,code,status):
        self.mic.setEnabled(self.robot_ready)
        if code:
            self.audio.setText('Thu/nhận dạng thất bại. Xem nhật ký và chọn lại micro.')

    def closeEvent(self,event):
        if self.process and self.process.state()!=QtCore.QProcess.NotRunning:
            self.process.terminate()
            self.process.waitForFinished(2000)
            if self.process.state()!=QtCore.QProcess.NotRunning:
                self.process.kill()
        event.accept()


def main():
    app=QtWidgets.QApplication(sys.argv)
    rclpy.init(args=[],signal_handler_options=SignalHandlerOptions.NO)
    node=Node('week7_voice_panel')
    panel=Panel(node)
    panel.show()
    def quit_panel(*_):
        panel.close()
        app.quit()
    signal.signal(signal.SIGINT,quit_panel)
    signal.signal(signal.SIGTERM,quit_panel)
    def snapshot(*_):
        QtCore.QTimer.singleShot(0, lambda: panel.grab().save(str(ROOT/'evidence/panel_preview.png')))
    signal.signal(signal.SIGUSR1, snapshot)
    if os.environ.get('WEEK7_PANEL_PREVIEW') == '1':
        QtCore.QTimer.singleShot(3000, snapshot)
    try:
        app.exec_()
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__=='__main__':
    main()
