import subprocess
import sys
import os
os.makedirs('tmp', exist_ok=True)
r = subprocess.run([sys.executable, '-m', 'pytest', 'backend/tests/test_whatsapp_chats.py::test_webhook_guarda_citacao_em_mensagem', '-q'], capture_output=True, text=True)
with open('tmp/whatsapp_single_result.txt', 'w', encoding='utf-8') as f:
	f.write('RC=' + str(r.returncode) + '\n')
	f.write(r.stdout or '')
	f.write(r.stderr or '')
