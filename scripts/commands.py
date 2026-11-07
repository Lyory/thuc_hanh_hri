import re
import unicodedata


def normalize(text):
    text = unicodedata.normalize('NFD', text.lower().replace('đ', 'd'))
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    return ' '.join(re.sub(r'[^a-z0-9 ]', ' ', text).split())


def parse_command(text, regions):
    text = normalize(text)
    if text in ('dung', 'dung lai', 'huy', 'huy dieu huong'):
        return []
    # Accept only a complete navigation command; every mentioned place is resolved.
    match = re.fullmatch(r'(?:di chuyen|di|hay di)(?: tu (.+)| den (.+))', text)
    if not match:
        raise ValueError('Câu lệnh không hợp lệ. Nói: Đi đến khu vực A; Đi từ A đến B.')
    aliases = {}
    for region in regions:
        for alias in [region['id'], region['name'], *region['aliases']]:
            key = normalize(alias)
            if key in aliases and aliases[key] != region['id']:
                raise ValueError('Cấu hình alias trùng nhau')
            aliases[key] = region['id']
    names = re.split(r' (?:roi quay lai|roi den|roi|qua|den) ', match[1] or match[2])
    if match[1] and len(names) < 2:
        raise ValueError('Lệnh từ ... phải có đích đến')
    result = []
    for name in names:
        if name not in aliases:
            raise ValueError(f'Khu vực không tồn tại: {name}')
        result.append(aliases[name])
    return result
