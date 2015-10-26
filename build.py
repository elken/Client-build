import os
import glob
import requests
import tempfile
import tarfile
import zipfile
import subprocess
import winreg
import shutil
from clint.textui import progress

paths = {"Qt": "C:\Qt",
         "Boost": "C:\Boost",
         "CMake": "C:\Program Files (x86)\CMake"}


def get_file_with_progress(url, file, do_tar=True, path="."):
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
        try:
            tar = tarfile.open(file, "r:*")
            if tarfile.is_tarfile(file):
                for item in tar:
                    print("Extracting %s" % item.name)
                    tar.extract(item, path)
            tar.close()
        except tarfile.ReadError:
            with zipfile.ZipFile(file, "r") as zip_file:
                for item in zip_file.namelist():
                    print("Extracting %s" % item)
                    zip_file.extract(item, path)


def check_paths():
    for dep_name, val in paths.items():
        if not os.path.exists(val):
            if input("%s not found in expected location, enter other path? [N/y] " % dep_name).lower() in ['yes', 'y']:
                while True:
                    path = input("Enter path for %s: " % dep_name)
                    if os.path.exists(path):
                        paths[dep_name] = path
                        break
                    else:
                        print("Path invalid, try again")
            else:
                if input("Install %s? [Y/n] " % dep_name).lower() in ['yes', 'y', '']:
                    eval("install_" + dep_name.lower() + "()")
                else:
                    print("%s not found, continuing anyway" % dep_name)
        else:
            print("Found %s, continuing" % dep_name)


def install_cmake():
    print("Install CMake")
    with tempfile.TemporaryDirectory() as tmp_dir:
        old_dir = os.getcwd()
        os.chdir(tmp_dir)

        get_file_with_progress("http://cmake.org/files/v3.3/cmake-3.3.2-win32-x86.exe",
                               "cmake-3.3.2-win32-x86.exe",
                               False)

        subprocess.call(["cmake-3.3.2-win32-x86.exe", "/S", "/D=C:\Program Files (x86)\CMake"],
                        stdout=subprocess.PIPE,
                        shell=True)
        os.chdir(old_dir)


def install_boost():
    print("Install Boost")
    with tempfile.TemporaryDirectory() as tmp_dir:
        old_dir = os.getcwd()
        os.chdir(tmp_dir)

        get_file_with_progress("http://sourceforge.net/projects/boost/files/latest/download?source=files",
                               "boost.tar.bz2",
                               True)

        file = glob.glob("boost_*")
        print("Moving %s to %s" % (tmp_dir + "\\" + file[0], paths["Boost"]))
        os.rename(tmp_dir + "\\" + file[0], paths["Boost"])
        os.chdir(old_dir)


def install_qt():
    print("Installing Qt")
    with tempfile.TemporaryDirectory() as tmp_dir:
        old_dir = os.getcwd()
        os.chdir(tmp_dir)

        get_file_with_progress("http://download.qt.io/official_releases/qt/5.5/5.5.1/"
                               "qt-opensource-windows-x86-mingw492-5.5.1.exe",
                               "qt-opensource-windows-x86-mingw492-5.5.1.exe",
                               False)

        subprocess.call("qt-opensource-windows-x86-mingw492-5.5.1.exe", stdout=subprocess.PIPE)
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
        if input("Would you like to download the Project Ascension source? [Y/n] ").lower() in ["yes", "y", ""]:
            pa_cmake_dir = clone_repo()
        else:
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

    if lib_cmake_dir == "" or mingw_bin_dir == "" or qt_dll_dir == "":
        print("Qt installation is broken, try re-installing.")
    else:
        print("Running cmake -G \"MinGW MakeFiles\" -DWITH_TESTS=true -DCMAKE_PREFIX_PATH=\"%s\" %s"
              % (lib_cmake_dir, pa_cmake_dir))
        os.environ["PATH"] = "C:\Program Files (x86)\CMake\\bin" + os.pathsep + mingw_bin_dir
        print(os.environ["PATH"])
        subprocess.call(["cmake",
                         "-G",
                         "MinGW Makefiles",
                         "-DCMAKE_PREFIX_PATH=" + lib_cmake_dir + " ",
                         pa_cmake_dir])
        subprocess.call(["mingw32-make"], shell=True)
        for dep in ["Qt5Core.dll",
                    "Qt5Widgets.dll",
                    "Qt5Core.dll",
                    "Qt5Gui.dll",
                    "Qt5Sql.dll",
                    "Qt5Network.dll",
                    "libstdc++-6.dll",
                    "libwinpthread-1.dll",
                    "libgcc_s_dw2-1.dll"]:
            print("Copying %s here" % os.path.join(qt_dll_dir + "\\" + dep))
            shutil.copy(os.path.join(qt_dll_dir + "\\" + dep), ".")


def clone_repo():
    clone_dir = ""
    while True:
        clone_dir = input("Where would you like to save Project Ascension? "
                          "\n(If the path doesn't exist, it will be created.) ")

        if clone_dir is "":
            print("Invalid path entered. Try again.")
        else:
            if not os.path.exists(clone_dir):
                os.mkdir(clone_dir)
            break

    if not os.path.isabs(clone_dir):
        clone_dir = os.path.abspath(clone_dir)

    with tempfile.TemporaryDirectory() as tmp_dir:
        old_dir = os.getcwd()
        os.chdir(tmp_dir)
        get_file_with_progress("http://github.com/Proj-Ascension/Client/archive/dev.zip", "dev.zip", True, clone_dir)

        os.chdir(old_dir)

    return os.path.join(clone_dir, "Client-dev")

if __name__ == "__main__":
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\Wow6432Node\Kitware\CMake 3.2.3") as key:
            paths["CMake"] = winreg.EnumValue(key, 0)[1]
    except FileNotFoundError:
        pass
    check_paths()
    run_cmake()
