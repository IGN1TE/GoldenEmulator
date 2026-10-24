from pathlib import Path
import base64
root = Path(__file__).resolve().parent
shell = (root/'src/shell.html').read_text(encoding='utf-8').replace('<!-- BRAND_ICON -->','data:image/png;base64,'+base64.b64encode((root/'GoldenEmulator-logo.png').read_bytes()).decode())
css = (root/'src/stage2.css').read_text(encoding='utf-8') + (root/'src/library_tools.css').read_text(encoding='utf-8') + (root/'src/development_plus.css').read_text(encoding='utf-8') + (root/'src/extra_features.css').read_text(encoding='utf-8')
css += (root/'src/hub.css').read_text(encoding='utf-8')
script = (root/'src/art.js').read_text(encoding='utf-8') + (root/'src/native.js').read_text(encoding='utf-8') + (root/'src/app.js').read_text(encoding='utf-8') + (root/'src/controller.js').read_text(encoding='utf-8') + (root/'src/library_tools.js').read_text(encoding='utf-8') + (root/'src/development_plus.js').read_text(encoding='utf-8') + (root/'src/extra_features.js').read_text(encoding='utf-8')
script += (root/'src/hub.js').read_text(encoding='utf-8')
(root/'GoldenEmulator.html').write_text(shell.replace('</style>', css+'\n</style>').replace('<!-- APP_SCRIPT -->','<script>\n'+script+'\n</script>'), encoding='utf-8')
print('Built GoldenEmulator.html')
