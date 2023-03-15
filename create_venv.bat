@echo off
:: This script will create a new python environment for you 
:: It is meant to be launched once.

:: Determine the desired version of Python (replace X.Y with the desired version)
set PYTHON_VERSION=3.10

:: Folder name containing venv (created from where you call the script)
set DIR_VENV=myenv

:: Create a virtual environment
py -%PYTHON_VERSION%  -m venv myenv

:: Activate the virtual environment
call myenv\Scripts\activate.bat

:: update setuptools to include automatic use of compiler
python.exe -m pip install --upgrade pip
pip install --upgrade setuptools

:: Install the required libraries
:: I don't know if it works
::pip install -r requirements.txt

:: Deactivate the virtual environment
:: call deactivate

pause