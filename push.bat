@echo off
set /p commit_log=please input commit Content:
git status
git add -A
git commit -m "%commit_log%"
git push origin master
pause