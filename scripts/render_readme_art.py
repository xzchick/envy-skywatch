"""Render the README artwork in assets/readme/ as animated SVGs.

Standard library only. The art is illustrative: terminal lines are fixed
text, not captured output, and all example hashes are synthetic. Animations
stop under prefers-reduced-motion.

    python scripts/render_readme_art.py
"""
from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(__file__).resolve().parent.parent / 'assets' / 'readme'

BG = '#050713'
PANEL = '#0a0e22'
INK = '#f2f4ff'
MUTED = '#b9c3df'
DIM = '#6f7898'
CYAN = '#35e8ff'
CYAN_SOFT = '#6ceaff'
PINK = '#ff3db4'
LAVENDER = '#ac8cff'
VIOLET = '#8547e8'
LINE = '#1f2547'
ACCENTS = {'pink': PINK, 'cyan': CYAN, 'lavender': LAVENDER}
FONT = 'font-family="Arial, Helvetica, sans-serif"'
MONO = 'font-family="Menlo, Consolas, \'Courier New\', monospace"'
REDUCED = '@media(prefers-reduced-motion:reduce){*{animation:none!important}}'

ICONS = {
    'terminal': '<rect x="2.5" y="4" width="19" height="16" rx="3"/><path d="M7 9l3 3-3 3M12.5 15H17"/>',
    'chip': '<rect x="6" y="6" width="12" height="12" rx="2"/><rect x="9.5" y="9.5" width="5" height="5" rx="1"/><path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4"/>',
    'key': '<circle cx="8" cy="15" r="5"/><path d="M11.5 11.5 20 3M16 4l3 3M14.5 8.5l2.5 2.5"/>',
    'search': '<circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5L21 21"/>',
    'scale': '<path d="M12 3v18M7 21h10M5 7h14"/><path d="M5 7l-3 7a3 3 0 0 0 6 0zM19 7l-3 7a3 3 0 0 0 6 0z"/>',
    'shield': '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M9 12l2 2 4-4"/>',
    'lock': '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
    'download': '<path d="M12 3v12M7 10l5 5 5-5"/><path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/>',
    'grid': '<rect x="3" y="3" width="7.5" height="7.5" rx="1.5"/><rect x="13.5" y="3" width="7.5" height="7.5" rx="1.5"/><rect x="3" y="13.5" width="7.5" height="7.5" rx="1.5"/><rect x="13.5" y="13.5" width="7.5" height="7.5" rx="1.5"/>',
    'list': '<path d="M9 6h12M9 12h12M9 18h12"/><circle cx="4.5" cy="6" r="1"/><circle cx="4.5" cy="12" r="1"/><circle cx="4.5" cy="18" r="1"/>',
    'sparkle': '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/><path d="M19 16l.7 2 2 .7-2 .7-.7 2-.7-2-2-.7 2-.7z"/>',
    'folder': '<path d="M3 6.5A1.5 1.5 0 0 1 4.5 5H10l2 2.5h7.5A1.5 1.5 0 0 1 21 9v9.5a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 18.5z"/>',
    'gear': '<circle cx="12" cy="12" r="3.2"/><path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3M5.3 5.3l2.1 2.1M16.6 16.6l2.1 2.1M5.3 18.7l2.1-2.1M16.6 7.4l2.1-2.1"/>',
    'wrench': '<path d="M14.5 6.5a4.5 4.5 0 0 0 5.9 5.9L21 13l-8 8-3-3 8-8-.6-.6a4.5 4.5 0 0 1-5.9-5.9l3 3 2-2z"/><path d="M3 21l6-6"/>',
    'flask': '<path d="M9 3h6M10 3v6l-5.5 9.5A1.7 1.7 0 0 0 6 21h12a1.7 1.7 0 0 0 1.5-2.5L14 9V3"/><path d="M7 15h10"/>',
    'scroll': '<path d="M6 3h11a2 2 0 0 1 2 2v13"/><path d="M6 3a2 2 0 0 0-2 2v2h4V5a2 2 0 0 0-2-2z"/><path d="M8 7v12a2 2 0 0 0 2 2h9a2 2 0 0 0 2-2v-1H12v1a2 2 0 0 1-2 2"/>',
    'clock': '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/>',
    'stop': '<circle cx="12" cy="12" r="9"/><rect x="9" y="9" width="6" height="6" rx="1"/>',
    'orbit': '<circle cx="12" cy="12" r="3"/><ellipse cx="12" cy="12" rx="10" ry="4.5" transform="rotate(-28 12 12)"/><circle cx="19.4" cy="7.8" r="1.6"/>',
    'repeat': '<path d="M4 9l3-3 3 3"/><path d="M7 6v7a3 3 0 0 0 3 3h10"/><path d="M20 15l-3 3-3-3"/><path d="M17 18v-7a3 3 0 0 0-3-3H4"/>',
    'bell': '<path d="M6 10a6 6 0 0 1 12 0c0 5 2 6 2 6H4s2-1 2-6z"/><path d="M10.5 20a1.8 1.8 0 0 0 3 0"/>',
    'radar': '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4.5"/><path d="M12 12l6.4-6.4"/><circle cx="16" cy="8" r="1.1"/>',
    'eye': '<path d="M2 12s3.6-6.5 10-6.5S22 12 22 12s-3.6 6.5-10 6.5S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
    'hash': '<path d="M9 3L7 21M17 3l-2 18M4 8.5h16M3 15.5h16"/>',
    'alert': '<path d="M12 3l9.5 17h-19z"/><path d="M12 10v4M12 17h.01"/>',
}


def icon(name, x, y, size=24, color=CYAN, width=1.8):
    return (f'<g transform="translate({x} {y}) scale({size / 24:.3f})" fill="none" stroke="{color}" '
            f'stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</g>')


def os_mark(name, x, y, size, color):
    s = size / 24
    if name == 'macos':
        art = (f'<path d="M16.4 12.7c0-2.3 1.9-3.4 2-3.5-1.1-1.6-2.8-1.8-3.4-1.8-1.4-.2-2.8.9-3.5.9-.7 0-1.9-.8-3-.8'
               f'-1.6 0-3 .9-3.8 2.3-1.6 2.8-.4 7 1.2 9.3.8 1.1 1.7 2.4 2.9 2.3 1.2 0 1.6-.7 3-.7s1.8.7 3 .7c1.3 0 2.1-1.1 2.8-2.3'
               f'.9-1.3 1.3-2.6 1.3-2.7 0 0-2.5-1-2.5-3.7z" fill="{color}"/>'
               f'<path d="M14.1 5.9c.6-.8 1.1-1.8 1-2.9-.9 0-2 .6-2.7 1.4-.6.7-1.1 1.8-1 2.8 1 .1 2.1-.5 2.7-1.3z" fill="{color}"/>')
    elif name == 'windows':
        art = (f'<g fill="{color}"><path d="M2.5 5.2 10.4 4v7.4H2.5z"/><path d="M11.5 3.9 21.5 2.5v8.9h-10z"/>'
               f'<path d="M2.5 12.6h7.9V20l-7.9-1.1z"/><path d="M11.5 12.6h10v8.9l-10-1.4z"/></g>')
    else:
        art = (f'<path d="M12 2c-2.6 0-4 2.1-4 4.8 0 1.6-.6 2.8-1.5 4.2C5.3 12.8 4 14.9 4 17.2 4 20 7.3 22 12 22s8-2 8-4.8'
               f'c0-2.3-1.3-4.4-2.5-6.2-.9-1.4-1.5-2.6-1.5-4.2C16 4.1 14.6 2 12 2z" fill="{color}"/>'
               f'<path d="M12 9.5c-2.2 0-3.6 3-3.6 6.2 0 2.4 1.5 4.3 3.6 4.3s3.6-1.9 3.6-4.3c0-3.2-1.4-6.2-3.6-6.2z" fill="{BG}" opacity=".85"/>'
               f'<circle cx="10.4" cy="6.6" r="1" fill="{BG}"/><circle cx="13.6" cy="6.6" r="1" fill="{BG}"/>'
               f'<path d="M10.6 8.4h2.8L12 10z" fill="{PINK}"/>')
    return f'<g transform="translate({x} {y}) scale({s:.3f})">{art}</g>'


def frame(title, desc, body, w, h, rx=20, css=''):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="title description">
  <title id="title">{escape(title)}</title>
  <desc id="description">{escape(desc)}</desc>
  <defs>
    <linearGradient id="edge"><stop stop-color="{PINK}" stop-opacity=".55"/><stop offset=".5" stop-color="{LAVENDER}" stop-opacity=".2"/><stop offset="1" stop-color="{CYAN}" stop-opacity=".65"/></linearGradient>
    <linearGradient id="neon"><stop stop-color="{PINK}"/><stop offset="1" stop-color="{CYAN}"/></linearGradient>
    <radialGradient id="cloud"><stop stop-color="#0d5666" stop-opacity=".45"/><stop offset="1" stop-color="{BG}" stop-opacity="0"/></radialGradient>
    <radialGradient id="rose"><stop stop-color="#a71c7d" stop-opacity=".22"/><stop offset="1" stop-color="{BG}" stop-opacity="0"/></radialGradient>
    <clipPath id="clip"><rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="{rx}"/></clipPath>
  </defs>
  <style>.signal{{animation:pulse 7s ease-in-out infinite}}@keyframes pulse{{0%,100%{{opacity:.45}}50%{{opacity:.95}}}}{css}{REDUCED}</style>
  <g clip-path="url(#clip)">
    <rect width="{w}" height="{h}" fill="{BG}"/>
    <ellipse cx="{w - 80}" cy="{h // 2}" rx="{min(300, w * .6):.0f}" ry="{min(220, h):.0f}" fill="url(#cloud)"/>
    <ellipse cx="90" cy="{h - 10}" rx="{min(340, w * .7):.0f}" ry="{min(220, h):.0f}" fill="url(#rose)"/>
    <g fill="#a8c7ed" opacity=".3"><circle cx="{w * .62:.0f}" cy="26" r="1"/><circle cx="{w * .78:.0f}" cy="{h - 24}" r="1"/><circle cx="{w - 30}" cy="43" r="1.2"/><circle cx="{w * .45:.0f}" cy="{h - 18}" r=".8"/></g>
{body}
  </g>
  <rect x=".75" y=".75" width="{w - 1.5}" height="{h - 1.5}" rx="{rx}" fill="none" stroke="url(#edge)" stroke-width="1.5"/>
</svg>
'''


def chip(x, y, label, mark, color):
    w = 30 + len(label) * 9.4 + 18
    return (f'<rect x="{x}" y="{y}" width="{w:.0f}" height="32" rx="16" fill="{color}" fill-opacity=".1" stroke="{color}" stroke-opacity=".55"/>'
            f'{os_mark(mark, x + 11, y + 7, 18, color)}<text x="{x + 36}" y="{y + 21}" fill="{INK}">{label}</text>')


def hero():
    w, h = 1280, 480
    stars = []
    for i in range(34):
        x, y = (i * 389 + 71) % w, (i * 157 + 29) % 300
        r = .6 + (i % 3) * .35
        stars.append(f'<circle class="tw tw{i % 4}" cx="{x}" cy="{y}" r="{r:.2f}"/>')
    horizon = 400
    floor = [f'<path d="M0 {horizon}H{w}" stroke="url(#neon)" stroke-opacity=".55" stroke-width="1.4"/>']
    for k in range(-12, 13):
        floor.append(f'<path d="M{640 + k * 40} {horizon}L{640 + k * 190} {h}"/>')
    rows = ''.join(f'<path class="row r{i}" d="M0 {horizon + 8}H{w}"/>' for i in range(4))

    tx, ty, tw, th = 712, 60, 520, 312
    lines = [
        ('cmd', 'envy-skywatch', 'opens the watch window'),
        ('cmd', 'envy-skywatch init watch.envywatch --title Review', 'watchlist created, revision 0'),
        ('cmd', 'envy-skywatch add watch w.r1 --pattern api_key', 'term added -> revision 1'),
        ('cmd', 'envy-skywatch scan w.r1 ./project', '3 high, 1 medium, 1 low'),
        ('cmd', 'envy-skywatch record w.r1 w.r2 ./project', 'scan logged -> revision 2'),
    ]
    cycle = 20
    body_lines, css = [], []
    y = ty + 66
    cw = 8.4
    for i, (_, command, reply) in enumerate(lines):
        start = 4 + i * 16.5
        typed = 5.5
        prompt_w = 6 * cw
        cmd_w = len(command) * cw + 4
        cover_x = tx + 22 + prompt_w
        body_lines.append(
            f'<g class="ln ln{i}"><text x="{tx + 22}" y="{y}" fill="{PINK}">$</text>'
            f'<text x="{cover_x:.1f}" y="{y}" fill="{INK}">{escape(command)}</text>'
            f'<rect class="cv cv{i}" x="{cover_x - 1:.1f}" y="{y - 14}" width="{cmd_w:.1f}" height="19" fill="{PANEL}"/></g>'
            f'<text class="ln rp{i}" x="{tx + 38}" y="{y + 21}" fill="{CYAN_SOFT}">{escape(reply)}</text>')
        steps = max(4, len(command))
        css.append(
            f'.ln{i}{{animation:ln{i} {cycle}s linear infinite}}'
            f'@keyframes ln{i}{{0%,{start:.1f}%{{opacity:0}}{start + .1:.1f}%,94%{{opacity:1}}97%,100%{{opacity:0}}}}'
            f'.cv{i}{{opacity:0;animation:cv{i} {cycle}s linear infinite}}'
            f'@keyframes cv{i}{{0%,{start:.1f}%{{opacity:1;transform:translateX(0);animation-timing-function:steps({steps},end)}}'
            f'{start + typed:.1f}%{{opacity:1;transform:translateX({cmd_w:.0f}px)}}{start + typed + .1:.1f}%,100%{{opacity:0;transform:translateX({cmd_w:.0f}px)}}}}'
            f'.rp{i}{{animation:rp{i} {cycle}s linear infinite}}'
            f'@keyframes rp{i}{{0%,{start + typed + 2:.1f}%{{opacity:0}}{start + typed + 3.5:.1f}%,94%{{opacity:1}}97%,100%{{opacity:0}}}}')
        y += 44
    cursor_y = y
    body = f'''    <defs>
      <linearGradient id="ttl" x2="1"><stop stop-color="{INK}"/><stop offset=".55" stop-color="#ffd1ee"/><stop offset="1" stop-color="{CYAN_SOFT}"/></linearGradient>
      <linearGradient id="fade" x1="0" y1="0" x2="0" y2="1"><stop stop-color="{BG}" stop-opacity="0"/><stop offset="1" stop-color="{BG}"/></linearGradient>
      <filter id="glow" x="-20%" y="-40%" width="140%" height="180%"><feGaussianBlur stdDeviation="9"/></filter>
      <radialGradient id="sun"><stop stop-color="{PINK}" stop-opacity=".5"/><stop offset=".6" stop-color="{VIOLET}" stop-opacity=".15"/><stop offset="1" stop-color="{BG}" stop-opacity="0"/></radialGradient>
    </defs>
    <ellipse cx="640" cy="{horizon}" rx="560" ry="90" fill="url(#sun)"/>
    <g fill="#c9d9ff">{''.join(stars)}</g>
    <g stroke="{LAVENDER}" stroke-opacity=".22" stroke-width="1">{''.join(floor[1:])}</g>
    <g stroke="{CYAN}" stroke-opacity=".35" stroke-width="1">{rows}</g>
    {floor[0]}
    <rect y="{horizon}" width="{w}" height="{h - horizon}" fill="url(#fade)"/>

    <g {MONO}><text x="66" y="92" font-size="15" letter-spacing="4" fill="{CYAN_SOFT}">ENCRYPTED  ·  WATCHLIST  ·  OFFLINE SCAN</text></g>
    <g {FONT} font-weight="700">
      <text class="flick" x="60" y="196" font-size="104" letter-spacing="3" fill="{PINK}" filter="url(#glow)">ENVY</text>
      <text x="60" y="196" font-size="104" letter-spacing="3" fill="url(#ttl)">ENVY</text>
      <text x="64" y="252" font-size="35" font-weight="400" letter-spacing="7" fill="{LAVENDER}">SKYWATCH</text>
    </g>
    <path d="M66 276h86" stroke="{PINK}" stroke-width="3" stroke-linecap="round"/>
    <path d="M160 276h40" stroke="{CYAN}" stroke-opacity=".6" stroke-width="3" stroke-linecap="round"/>
    <g {FONT} font-size="22" fill="{MUTED}">
      <text x="66" y="316">Watch for what matters.</text>
      <text x="66" y="346">Scan a file or folder, offline.</text>
    </g>
    <g {FONT} font-size="14" font-weight="600" letter-spacing="1.2">
      {chip(66, 368, 'macOS', 'macos', PINK)}
      {chip(176, 368, 'Windows', 'windows', CYAN)}
      {chip(302, 368, 'Linux', 'linux', LAVENDER)}
    </g>

    <g class="float">
      <rect x="{tx + 8}" y="{ty + 12}" width="{tw}" height="{th}" rx="16" fill="{VIOLET}" opacity=".18" filter="url(#glow)"/>
      <rect x="{tx}" y="{ty}" width="{tw}" height="{th}" rx="14" fill="{PANEL}" stroke="url(#edge)" stroke-width="1.4"/>
      <path d="M{tx} {ty + 38}H{tx + tw}" stroke="{LINE}"/>
      <circle cx="{tx + 22}" cy="{ty + 19}" r="5.5" fill="{PINK}"/><circle cx="{tx + 40}" cy="{ty + 19}" r="5.5" fill="{LAVENDER}"/><circle cx="{tx + 58}" cy="{ty + 19}" r="5.5" fill="{CYAN}"/>
      <text x="{tx + tw / 2}" y="{ty + 24}" font-size="12.5" fill="{DIM}" text-anchor="middle" {MONO}>envy-skywatch · encrypted · local</text>
      <g {MONO} font-size="14">{''.join(body_lines)}
        <text x="{tx + 22}" y="{cursor_y}" fill="{PINK}">$</text>
        <rect class="cur" x="{tx + 22 + 2 * cw:.1f}" y="{cursor_y - 14}" width="8" height="18" fill="{CYAN}"/>
      </g>
    </g>'''
    css.append('.cur{animation:blink 1.1s steps(1) infinite}@keyframes blink{50%{opacity:0}}'
               '.flick{opacity:.75;animation:flick 7s linear infinite}@keyframes flick{0%,17%,21%,63%,65%,100%{opacity:.75}19%,64%{opacity:.2}40%{opacity:.95}}'
               '.float{animation:float 8s ease-in-out infinite}@keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-6px)}}'
               '.tw{opacity:.35;animation:tw 5s ease-in-out infinite}.tw1{animation-delay:-1.3s}.tw2{animation-delay:-2.6s}.tw3{animation-delay:-3.9s}'
               '@keyframes tw{0%,100%{opacity:.15}50%{opacity:.85}}'
               '.row{animation:row 4s linear infinite}.r1{animation-delay:-1s}.r2{animation-delay:-2s}.r3{animation-delay:-3s}'
               f'@keyframes row{{0%{{transform:translateY(0);opacity:.1}}20%{{opacity:.8}}100%{{transform:translateY({h - horizon - 8}px);opacity:0}}}}')
    return frame('ENVY SkyWatch', 'A native desktop window for encrypted watchlists and offline content scanning on macOS, Windows and Linux: '
                 'keep terms to watch for, scan a file or folder, and read every hit with its file, line and context. '
                 'Illustrative terminal: ' + '; '.join(c for _, c, _ in lines) + '.', body, w, h, rx=24, css=''.join(css))


def section(sid, title, kicker, ico, accent):
    w, h = 1000, 76
    a = ACCENTS[accent]
    tw = len(title) * 15.5
    line_x = 74 + tw + 24
    line_end = w - 40 - len(kicker) * 9.6
    body = f'''    <defs><filter id="glow" x="-20%" y="-60%" width="140%" height="220%"><feGaussianBlur stdDeviation="5"/></filter></defs>
    <g class="flicker" filter="url(#glow)">{icon(ico, 28, 23, 30, a, 2.6)}
      <text x="74" y="48" font-size="27" font-weight="700" fill="{a}" {FONT}>{escape(title)}</text></g>
    {icon(ico, 28, 23, 30, a)}
    <text x="74" y="48" font-size="27" font-weight="700" letter-spacing=".4" fill="{INK}" {FONT}>{escape(title)}</text>
    <text x="{w - 30}" y="47" font-size="12.5" letter-spacing="2.4" font-weight="600" fill="{a}" text-anchor="end" {FONT}>{escape(kicker)}</text>
    <path d="M{line_x:.0f} 39H{line_end:.0f}" stroke="{a}" stroke-opacity=".25" stroke-width="1.5"/>
    <g class="travel"><circle cx="{line_x:.0f}" cy="39" r="5" fill="{a}" opacity=".3"/><circle cx="{line_x:.0f}" cy="39" r="2" fill="#fff"/></g>'''
    run = line_end - line_x
    css = ('.flicker{animation:flicker 6s linear infinite}'
           '@keyframes flicker{0%,18%,22%,62%,64%,100%{opacity:.85}20%,63%{opacity:.25}40%{opacity:1}}'
           f'.travel{{animation:travel 5s ease-in-out infinite}}@keyframes travel{{0%{{transform:translateX(0);opacity:0}}15%{{opacity:1}}85%{{opacity:1}}100%{{transform:translateX({run:.0f}px);opacity:0}}}}')
    return f'section-{sid}.svg', frame(title, f'{title}: {kicker}', body, w, h, rx=16, css=css)


FEATURES = [
    ('lock', 'Encrypted watchlist', 'Terms and scan history', 'sealed with AES-256-GCM.', 'aes-256-gcm', PINK),
    ('radar', 'Offline scan', 'Scan a file or a whole folder', 'for every term, locally.', 'file or folder', CYAN),
    ('eye', 'Hit in context', 'Every hit with its file, line', 'and the matching snippet.', 'file : line', LAVENDER),
    ('hash', 'Keyword or hash', 'Watch a case-insensitive word,', 'or a file by its SHA-256.', 'text · sha256', PINK),
    ('scroll', 'Scan journal', 'Record a scan into a', 'SHA-256 hash-chained journal.', 'hash chain', CYAN),
    ('scale', 'Honest by design', 'A hit is a literal match', '— not a verdict.', 'no overclaiming', LAVENDER),
]


def features():
    w, h = 1000, 400
    cw, ch, gap = 300, 160, 20
    x0, y0 = (w - 3 * cw - 2 * gap) / 2, 30
    cards, css = [], []
    for i, (ico, title, l1, l2, cmd, a) in enumerate(FEATURES):
        x, y = x0 + (i % 3) * (cw + gap), y0 + (i // 3) * (ch + gap + 10)
        cards.append(f'''    <g class="fc fc{i}">
      <rect x="{x:.0f}" y="{y}" width="{cw}" height="{ch}" rx="16" fill="{PANEL}" fill-opacity=".85" stroke="{a}" stroke-opacity=".35"/>
      <circle cx="{x + 42:.0f}" cy="{y + 42}" r="22" fill="{a}" fill-opacity=".12"/>
      {icon(ico, x + 30, y + 30, 24, a, 2)}
      <text x="{x + 78:.0f}" y="{y + 49}" font-size="20" font-weight="700" fill="{INK}" {FONT}>{escape(title)}</text>
      <text x="{x + 24:.0f}" y="{y + 92}" font-size="15" fill="{MUTED}" {FONT}>{escape(l1)}</text>
      <text x="{x + 24:.0f}" y="{y + 113}" font-size="15" fill="{MUTED}" {FONT}>{escape(l2)}</text>
      <text x="{x + 24:.0f}" y="{y + 142}" font-size="13" fill="{a}" {MONO}>{escape(cmd)}</text>
      <rect class="sh" x="{x:.0f}" y="{y}" width="{cw}" height="3" rx="1.5" fill="{a}" opacity=".0"/>
    </g>''')
        css.append(f'.fc{i} .sh{{animation:sh 9s ease-in-out {-i * 1.5:.1f}s infinite}}')
    css.append('@keyframes sh{0%,100%{opacity:0}45%,55%{opacity:.9}}')
    desc = '; '.join(f'{f[1]}: {f[2]} {f[3]} ({f[4]})' for f in FEATURES)
    return frame('What ENVY SkyWatch does', desc, '\n'.join(cards), w, h, rx=20, css=''.join(css))


OS_CARDS = [
    ('macos', 'macOS', PINK, [('window', 'Native Cocoa window'), ('engine', 'bundled Python + Qt'), ('needs', 'no dependencies'), ('install', '.app bundle or pip')]),
    ('windows', 'Windows', CYAN, [('window', 'Native Win32 window'), ('engine', 'bundled Python + Qt'), ('needs', 'no dependencies'), ('install', '.exe bundle or pip')]),
    ('linux', 'Linux', LAVENDER, [('window', 'X11 / Wayland window'), ('engine', 'bundled Python + Qt'), ('needs', 'no dependencies'), ('install', 'tarball or pip')]),
]


def os_card(mark, name, a, facts):
    w, h = 340, 230
    rows = []
    for j, (k, v) in enumerate(facts):
        y = 112 + j * 28
        rows.append(f'<text x="26" y="{y}" fill="{a}">{k}</text><text x="104" y="{y}" fill="{INK}">{escape(v)}</text>')
    body = f'''    <circle class="signal" cx="58" cy="56" r="30" fill="{a}" fill-opacity=".14"/>
    {os_mark(mark, 40, 37, 36, a)}
    <text x="102" y="52" font-size="25" font-weight="700" fill="{INK}" {FONT}>{name}</text>
    <text x="103" y="73" font-size="11.5" letter-spacing="2" font-weight="600" fill="{a}" {FONT}>SUPPORTED</text>
    <path d="M26 88H{w - 26}" stroke="{LINE}"/>
    <g {MONO} font-size="12.5">{''.join(rows)}</g>'''
    return f'os-{mark}.svg', frame(f'{name}: supported', f'{name}: ' + ', '.join(f'{k} {v}' for k, v in facts), body, w, h, rx=18)


YES, NO = 'yes', 'no'
MATRIX = [
    ('Native application window', YES, YES, YES),
    ('Encrypted watchlist (AES-256-GCM)', YES, YES, YES),
    ('Keyword and file-hash terms', YES, YES, YES),
    ('Scan a file or a whole folder', YES, YES, YES),
    ('Hit with file, line and context', YES, YES, YES),
    ('Hash-chained scan journal', YES, YES, YES),
    ('Revision-preserving saves', YES, YES, YES),
    ('Plaintext HTML / JSON report', YES, YES, YES),
    ('Terminal mode (CLI)', YES, YES, YES),
    ('Standalone bundle (no Python)', 'arm64', 'x86_64', 'x86_64'),
    ('Python package (pip install)', YES, YES, YES),
    ('Built and tested in CI', YES, YES, YES),
]


def matrix():
    w = 1000
    top, rh = 96, 38
    h = top + len(MATRIX) * rh + 26
    cols = [(560, 'macos', 'macOS', PINK), (720, 'windows', 'Windows', CYAN), (880, 'linux', 'Linux', LAVENDER)]
    head = ''.join(f'{os_mark(m, x + 12 - (30 + len(n) * 9.6) / 2, 34, 22, a)}<text x="{x + 12 - (30 + len(n) * 9.6) / 2 + 30:.1f}" y="51" font-size="17" font-weight="700" fill="{INK}" {FONT}>{n}</text>'
                   for x, m, n, a in cols)
    rows = []
    for i, (feature, *cells) in enumerate(MATRIX):
        y = top + i * rh
        band = f'<rect x="20" y="{y}" width="{w - 40}" height="{rh}" rx="8" fill="#ffffff" fill-opacity=".028"/>' if i % 2 == 0 else ''
        out = [band, f'<text x="40" y="{y + 25}" font-size="15.5" fill="{MUTED}" {FONT}>{escape(feature)}</text>']
        for c, ((x, _, _, a), cell) in enumerate(zip(cols, cells)):
            cx, cy = x + 12, y + rh / 2
            if cell == YES:
                out.append(f'<g class="ok" style="animation-delay:{-(i * 3 + c) * .25:.2f}s">'
                           f'<circle cx="{cx}" cy="{cy}" r="11" fill="{a}" fill-opacity=".16" stroke="{a}" stroke-opacity=".6"/>'
                           f'<path d="M{cx - 5} {cy}l3.5 3.5 6.5-7" fill="none" stroke="{a}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></g>')
            elif cell == NO:
                out.append(f'<path d="M{cx - 7} {cy}h14" stroke="{DIM}" stroke-width="2" stroke-linecap="round"/>')
            else:
                out.append(f'<text x="{cx}" y="{cy + 5}" font-size="12.5" fill="{a}" text-anchor="middle" {MONO}>{escape(cell)}</text>')
        rows.append(''.join(out))
    body = f'''    <g {FONT}><text x="40" y="51" font-size="13" letter-spacing="2.4" font-weight="600" fill="{CYAN_SOFT}">FEATURE</text></g>
    {head}
    <path d="M30 76H{w - 30}" stroke="url(#neon)" stroke-opacity=".5"/>
    {''.join(rows)}'''
    css = '.ok{animation:pop 6s ease-in-out infinite}@keyframes pop{0%,100%{opacity:.75}50%{opacity:1}}'
    desc = '; '.join(f'{f}: macOS {m}, Windows {wi}, Linux {l}' for f, m, wi, l in MATRIX)
    return frame('Compatibility by operating system', desc, body, w, h, rx=20, css=css)


SECTIONS = [
    ('features', 'What It Does', 'WATCH · SCAN · RECORD', 'radar', 'pink'),
    ('works-on', 'Works On', 'MACOS · WINDOWS · LINUX', 'grid', 'cyan'),
    ('install', 'Install', 'APP OR PIP', 'download', 'pink'),
    ('use', 'Using It', 'WINDOW OR TERMINAL', 'list', 'lavender'),
    ('safety', 'Honest By Design', 'A MATCH, NOT A VERDICT', 'scale', 'cyan'),
    ('build', 'Build & Test', 'FOR CONTRIBUTORS', 'wrench', 'pink'),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    files = {'hero.svg': hero(), 'features.svg': features(), 'compat.svg': matrix()}
    files.update(os_card(*c) for c in OS_CARDS)
    files.update(section(*s) for s in SECTIONS)
    for name, svg in files.items():
        (OUT / name).write_text(svg, encoding='utf-8')
    print(f'Wrote {len(files)} files to {OUT}')


if __name__ == '__main__':
    main()
