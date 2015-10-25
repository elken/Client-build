# Flow
# 1. Check paths
# 2. Prompt user to check other paths
# 3. If not exist, install
# 4. Prompt user for build config (VS, Ninja, etc)
# 5. Run cmake

import os
import glob
import requests
import tempfile
import tarfile
import subprocess
import winreg
import shutil
from clint.textui import progress

paths = {"Qt": "C:\Qt",
         "Boost": "C:\Boost",
         "CMake": "C:\Program Files (x86)\CMake"}


def get_file_with_progress(url, file, do_tar=True):
    r = requests.get(url, stream=True)
    with open(file, "wb") as f:
        print("Downloading %s" % file)
        total_length = int(r.headers.get('content-length'))
        for chunk in progress.bar(r.iter_content(chunk_size=1024), expected_size=(total_length/1024) + 1):
            if chunk:
                f.write(chunk)
                f.flush()
        f.close()
        r.close()
    if do_tar:
        tar = tarfile.open(file, "r:bz2")
        if tarfile.is_tarfile(file):
            for item in tar:
                print("Extracting %s" % item.name)
                tar.extract(item)
        tar.close()


def check_paths():
    for key, val in paths.items():
        if not os.path.exists(val):
            if input("%s not found in expected location, enter other path? [N/y] " % key).lower() in ['yes', 'y']:
                while True:
                    path = input("Enter path for %s: " % key)
                    if os.path.exists(path):
                        paths[key] = path
                        break
                    else:
                        print("Path invalid, try again")
            else:
                if input("Install %s? [Y/n] " % key).lower() in ['yes', 'y', '']:
                    eval("install_" + key.lower() + "()")
                else:
                    print("%s not found, continuing anyway" % key)
        else:
            print("Found %s, continuing" % key)


def install_cmake():
    print("Install CMake")
    with tempfile.TemporaryDirectory() as tmp_dir:
        old_dir = os.getcwd()
        os.chdir(tmp_dir)
        print("Using %s as tempdir" % tmp_dir)
        url = "http://cmake.org/files/v3.3/cmake-3.3.2-win32-x86.exe"
        file = "cmake-3.3.2-win32-x86.exe"

        get_file_with_progress(url, file, False)

        subprocess.call([file, "/S", "/D=C:\Program Files (x86)\CMake"], stdout=subprocess.PIPE, shell=True)
        os.chdir(old_dir)


def install_boost():
    print("Install Boost")
    with tempfile.TemporaryDirectory() as tmp_dir:
        old_dir = os.getcwd()
        os.chdir(tmp_dir)
        print("Using %s as tempdir" % tmp_dir)
        url = "http://sourceforge.net/projects/boost/files/latest/download?source=files"
        file = "boost.tar.bz2"

        get_file_with_progress(url, file, True)

        file = glob.glob("boost_*")
        print("Moving %s to %s" % (tmp_dir + "\\" + file[0], paths["Boost"]))
        os.rename(tmp_dir + "\\" + file[0], paths["Boost"])
        os.chdir(old_dir)


def install_qt():
    print("Installing Qt")
    with tempfile.TemporaryDirectory() as tmp_dir:
        old_dir = os.getcwd()
        os.chdir(tmp_dir)
        print("Using %s as tempdir" % tmp_dir)
        url = "http://download.qt.io/official_releases/qt/5.5/5.5.1/qt-opensource-windows-x86-mingw492-5.5.1.exe"
        file = "qt-opensource-windows-x86-mingw492-5.5.1.exe"

        get_file_with_progress(url, file, False)

        subprocess.call(file, stdout=subprocess.PIPE)
        os.chdir(old_dir)


def run_cmake():
    if not os.path.exists("build"):
        os.mkdir("build")
    os.chdir("build")
    qt_dll_dir = ""
    mingw_bin_dir = ""
    lib_cmake_dir = ""
    pa_cmake_dir = ""
    if not os.path.exists("CMakeLists.txt") or not os.path.exists("../CMakeLists.txt"):
        while True:
            pa_cmake_dir = input("Enter the path of the Project Ascension source code (with CMakeLists.txt in) ")
            if os.path.exists(os.path.join(pa_cmake_dir, "CMakeLists.txt")):
                print("Found source code, building")
                break
            else:
                print("Directory is missing CMakeLists.txt, please try again.")
    for folder, subs, files in os.walk(paths["Qt"]):
        if folder.endswith("mingw492_32\lib\cmake"):
            lib_cmake_dir = folder
        if folder.endswith("mingw492_32\\bin"):
            mingw_bin_dir = folder
        if folder.endswith("5.5\mingw492_32\\bin"):
            qt_dll_dir = folder
    print("Running cmake -G \"MinGW MakeFiles\" -DWITH_TESTS=true -DCMAKE_PREFIX_PATH=\"%s\" %s"
          % (lib_cmake_dir, pa_cmake_dir))
    os.environ["PATH"] = "C:\Program Files (x86)\CMake\\bin" + os.pathsep + mingw_bin_dir
    print(os.environ["PATH"])
    subprocess.call(["cmake",
                     "-G",
                     "MinGW Makefiles",
                     "-DWITH_TESTS=true",
                     "-DCMAKE_PREFIX_PATH=" + lib_cmake_dir + " ",
                     pa_cmake_dir])
    subprocess.call(["mingw32-make"], shell=True)
    for dep in ["Qt5Core.dll", "Qt5Widgets.dll", "Qt5Core.dll", "Qt5Gui.dll", "Qt5Sql.dll", "libstdc++-6.dll", "libwinpthread-1.dll", "libgcc_s_dw2-1.dll"]:
        print("Copying %s here" % os.path.join(qt_dll_dir + "\\" + dep))
        shutil.copy(os.path.join(qt_dll_dir + "\\" + dep), ".")


if __name__ == "__main__":
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\Wow6432Node\Kitware\CMake 3.2.3") as key:
            paths["CMake"] = winreg.EnumValue(key, 0)[1]
    except FileNotFoundError:
        pass
    check_paths()
    run_cmake()
