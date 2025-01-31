Run Claude AI:
1. add `.ENV` file and add `ANTHROPIC_API_KEY={your-key}`
2. run this command `source .venv/bin/activate && python3 app.py`

Create .bat file to run it 

```
@echo off
REM Advanced script to launch ClaudeUI in WSL with more flexibility

REM Launch the application minimized and detached
start /B "" wsl -e bash -ic "cd && cd ClaudeUI && source .venv/bin/activate && python3 app.py"

REM Exit the batch script
exit
```
