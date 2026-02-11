@echo off
title Chorus Platform — PRODUCTION MODE (Supabase + Vercel)

echo.
echo =========================================================================
echo  CHORUS PLATFORM — PRODUCTION MODE
echo =========================================================================
echo.
echo  [1/2] Checking environment...
echo        - Backend: SUPABASE (Cloud)
echo        - Frontend: PORTAL (Localhost)
echo.
echo  [2/2] Starting Portal Web Server...
echo        - Serving ./portal on port 8888
echo.
echo  ACCESS THE PORTAL: http://localhost:8888
echo.
echo  NOTE: Agents are now managed via Supabase.
echo        To publish agents, use 'python demo/supabase_demo.py'
echo        or integrate the SDK in your own scripts.
echo.

cd portal
python -m http.server 8888
pause
