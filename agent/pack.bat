pyinstaller -w -F .\agent.py
pyarmor gen -O obfdist --pack dist/agent agent.py
