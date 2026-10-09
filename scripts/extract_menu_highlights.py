"""Preserve Menu copy, using reviewed labels to disambiguate PDF column order."""
import hashlib
import json
import re
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / 'references/private/product-source-documents/01Product Menu_highlights.pdf'

# Labels are transcribed from the source, including its spelling. Display edits
# are separate so that extraction never silently rewrites the author's copy.
SPECS = [
    ('北京', [
        ['Tiananmen, Forbidden City & Jingshan Park', 'Beijing Hutong Light Walk / Cycling'],
        ['The Great Wall at Mutianyu', 'Summer Palace'], ['Temple of Heaven', 'Yonghe Temple (Lama Temple)'],
    ], ['Peking Opera & Dinner', 'Hanfu Shooting']),
    ('西安', [['Terracotta Army & Mausoleum Park'], ['Xi’an City Wall', 'Big Wild Goose Pagoda', 'Bell/Drum Towers & Muslim Quarter']],
     ['Tang Dynasty Palace Show', 'Tang Paradise & Everbright City', 'Terracotta Warrior DIY Workshop']),
    ('上海', [['People’s Park & Shanghai Museum', 'The Bund Citywalk', 'Yu Garden & City God Temple'], ['Site of the First CCP Congress', 'Jing’an Temple & Wukang Road Walk'], ['Zhujiajiao Water Town'], ['Shanghai Disneyland']],
     ['Huangpu River Night Cruise', 'Zujiajiao Cloth Workshop', 'Hanfu Shooting']),
    ('广州', [['Chen Clan Ancestral Hall & Shamian Island & Yongqing Fang', 'Xiguan Folk Museum & Guangzhou Thirteen-Hongs Museum & Guangzhou Tower'], ['Yuexiu Park & Museum of the Nanyue King', 'Sun Yat-sen Memorial Sites & Huiji Old Streets'], ['Gu Long Gorge Day Trip'], ['Wholesale Market Deep Dive']],
     ['Wellness SPA', 'Wing Chun Kung Fu', 'Live-Streaming Hub Visit']),
    ('重庆', [['Great Hall & Shancheng Lane', 'Yangtze River Cableway', 'Xiahao Li Old Street'], ['Wulong Karst'], ['Dazu Carvings', 'Ciqikou Town'], ['Fengdu Ghost City', '“War Flames of the Three Kingdoms”', 'Wuxia (Witch) Gorge Sailing', 'Three Gorges Dam']], ['Sichuan Opera Face-Changing']),
    ('阳朔', [['Yulong River Bamboo Raft', 'Ten-Mile Gallery Cycling', 'West Street Stroll'], ['Xingping Ancient Town', 'Li River Motorized Raft', 'Xianggong Hill Climb'], ['All-Terrain ATV', 'Chinese Cooking Class', 'Karst Cave Exploration', 'Via Ferrata Climb']], []),
    ('张家界', [['Tianmen Mountain Excursion'], ['Golden Whip Stream', 'Yuanjiajie & Tianzi Mountain'], ['Furong (Hibiscus) Town', 'Miao Long-table Banquet', 'Phoenix Ancient Town'], ['Qixingshan Via Ferrata', '72 Strange Towers']], ['Charming Xiangxi Show']),
    ('贵州', [['Jiaxiu Tower', 'Qingyan Ancient Town', 'Shidong Miao Silversmith Village', 'Xiasi Ancient Town', 'Zhaoxing Dong Village', 'Xiaoqikong National Park']], ['Shidong Market', 'Zhaoxing Batik Experience', 'Guizhou Craft Brewing', 'Hands-on silver-making workshop']),
    ('云南', [['Kunming Old Street', 'Dali Old Town', 'Erhai Lake & Xizhou Town', 'Lijiang Old Town (Dayan)', 'Black Dragon Pool', 'Tiger Leaping Gorge', 'Shangri-La & Dukezong', 'Pudacuo National Park']], ['Bai Three-Course Tea Ceremony', 'Tibetan Thangka Painting Class']),
]


def clean(text):
    return re.sub(r'\s+', ' ', text).strip(' :\n')


def label_pattern(name):
    # The PDF wraps even hyphenated names across lines.
    return re.escape(name).replace(r'\ ', r'\s+').replace(r'\-', r'-\s*')


def extract():
    reader = PdfReader(PDF)
    target = ROOT / 'data/products/attraction_highlights.json'
    previous = json.loads(target.read_text())
    archive = {'source': PDF.name, 'sha256': hashlib.sha256(PDF.read_bytes()).hexdigest(), 'pages': []}
    for index, (city, route_labels, activity_labels) in enumerate(SPECS):
        text = reader.pages[index].extract_text()
        archive['pages'].append({'page': index + 1, 'city': city, 'text': text})
        headings = list(re.finditer(r'Route\s+(\d+):\s*', text))
        labels = [name for group in route_labels for name in group] + activity_labels
        matches = {}
        for name in labels:
            match = re.search(label_pattern(name) + r'\s*\((\d[^)]*h)\)', text)
            if not match:
                raise ValueError(f'Page {index + 1}: missing label {name}')
            matches[name] = match
        boundaries = [m.start() for m in matches.values()] + [m.start() for m in headings]
        for marker in ['Hexa China Tours', 'Attraction Highlights', 'Fun Experience and Activities', 'Choice of Adventure:']:
            boundaries += [m.start() for m in re.finditer(re.escape(marker), text)]

        def item(name):
            match = matches[name]
            end = min([value for value in boundaries if value >= match.end()] + [len(text)])
            chunk = text[match.end():end]
            price = re.search(r'Price:\s*([^\n]+)', chunk)
            description = re.split(r'Price:', chunk)[0]
            return {'name': name, 'duration': clean(match.group(1)), 'description': clean(description), **({'price': clean(price.group(1))} if price else {})}

        routes = {}
        for number, names in enumerate(route_labels, 1):
            if headings:
                heading = headings[number - 1]
                line_end = text.index('\n', heading.end())
                title = clean(text[heading.end():line_end])
                desc_start = line_end + 1
                if city == '广州' and number == 4:
                    second_end = text.index('\n', desc_start)
                    title += ' ' + clean(text[desc_start:second_end])
                    desc_start = second_end + 1
                desc_end = min([value for value in boundaries if value >= desc_start] + [len(text)])
            else:
                line_end = text.index('\n')
                title, desc_start = clean(text[:line_end]), line_end + 1
                desc_end = min(match.start() for match in matches.values())
            description = clean(text[desc_start:desc_end])
            # Keep raw source above; exclude the known Guizhou paste error in display copy.
            if city == '贵州':
                description = description[description.index('Venture beyond'):]
            routes[f'Route {number}'] = {'title': title, 'description': description, 'attractions': [item(name) for name in names], 'source_page': index + 1}
        previous[city]['routes'] = routes
        previous[city]['activities'] = {name: {key: value for key, value in item(name).items() if key != 'name'} for name in activity_labels}
    target.write_text(json.dumps(previous, ensure_ascii=False, indent=2) + '\n')
    # Raw source is kept privately; it is never imported by the website or API.
    (PDF.parent / 'menu-extracted-source.json').write_text(json.dumps(archive, ensure_ascii=False, indent=2) + '\n')
    print('Extracted 24 routes, 2 long-route introductions and 19 experiences; Chengdu retained separately.')


if __name__ == '__main__':
    extract()
