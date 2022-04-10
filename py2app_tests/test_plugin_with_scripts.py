import sys
import unittest
import subprocess
import shutil
import time
import os
import signal
from distutils.sysconfig import get_config_var
from distutils.version import LooseVersion
import py2app
import platform

if __name__ == "__main__":
    from tools import kill_child_processes
else:
    from .tools import kill_child_processes

try:
    unichr
except NameError:
    unichr = chr

DIR_NAME = os.path.dirname(os.path.abspath(__file__))


class TestBasicPlugin(unittest.TestCase):
    plugin_dir = os.path.join(DIR_NAME, "plugin_with_scripts")
    py2app_args = []

    # Basic setup code
    #
    # The code in this block needs to be moved to
    # a base-class.
    @classmethod
    def setUpClass(cls):
        try:
            if os.path.exists(os.path.join(cls.plugin_dir, "build")):
                shutil.rmtree(os.path.join(cls.plugin_dir, "build"))

            if os.path.exists(os.path.join(cls.plugin_dir, "dist")):
                shutil.rmtree(os.path.join(cls.plugin_dir, "dist"))

            cmd = [sys.executable, "setup.py", "py2app"] + cls.py2app_args

            env = os.environ.copy()
            env["TMPDIR"] = os.getcwd()
            pp = os.path.dirname(os.path.dirname(py2app.__file__))
            if "PYTHONPATH" in env:
                env["PYTHONPATH"] = pp + ":" + env["PYTHONPATH"]
            else:
                env["PYTHONPATH"] = pp

            if "LANG" not in env:
                env["LANG"] = "en_US.UTF-8"

            p = subprocess.Popen(
                cmd,
                cwd=cls.plugin_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                close_fds=False,
                env=env,
            )
            lines = p.communicate()[0]
            if p.wait() != 0:
                print(lines)
                raise AssertionError("Creating basic_plugin bundle failed")

            p = subprocess.Popen(
                ["xcode-select", "-print-path"], stdout=subprocess.PIPE
            )
            lines = p.communicate()[0]
            if p.wait() != 0:
                raise AssertionError("Fetching Xcode root failed")

            if LooseVersion(platform.mac_ver()[0]) < LooseVersion("10.7"):
                cc = [get_config_var("CC")]
                env = dict(os.environ)
                env["MACOSX_DEPLOYMENT_TARGET"] = get_config_var(
                    "MACOSX_DEPLOYMENT_TARGET"
                )
            else:
                cc = ["xcrun", "clang"]
                env = dict(os.environ)

            cflags = get_config_var("CFLAGS").split()
            ldflags = get_config_var("LDFLAGS").split()
            if LooseVersion(platform.mac_ver()[0]) >= LooseVersion("10.14"):
                for idx, val in enumerate(cflags):
                    if val == "-arch" and cflags[idx + 1] == "i386":
                        del cflags[idx + 1]
                        del cflags[idx]
                        break

                for idx, val in enumerate(ldflags):
                    if val == "-arch" and ldflags[idx + 1] == "i386":
                        del ldflags[idx + 1]
                        del ldflags[idx]
                        break

            p = subprocess.Popen(
                cc
                + ldflags
                + cflags
                + [
                    "-o",
                    "bundle_loader",
                    os.path.join(DIR_NAME, "bundle_loader.m"),
                    "-framework",
                    "Foundation",
                ],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                close_fds=False,
            )
            lines = p.communicate()[0]
            if p.wait() != 0:
                print(lines)
                raise AssertionError("Creating bundle_loader failed")

        except:  # noqa: E722, B001
            cls.tearDownClass()
            raise

    @classmethod
    def tearDownClass(cls):
        if os.path.exists("bundle_loader"):
            os.unlink("bundle_loader")

        if os.path.exists(os.path.join(cls.plugin_dir, "build")):
            shutil.rmtree(os.path.join(cls.plugin_dir, "build"))

        if os.path.exists(os.path.join(cls.plugin_dir, "dist")):
            shutil.rmtree(os.path.join(cls.plugin_dir, "dist"))

        time.sleep(2)

    def tearDown(self):
        kill_child_processes()
        time.sleep(1)

    def start_app(self):
        # Start the test app, return a subprocess object where
        # stdin and stdout are connected to pipes.
        cmd = [
            "./bundle_loader",
            os.path.join(self.plugin_dir, "dist/BasicPlugin.bundle"),
        ]
        p = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            close_fds=False,
        )
        # stderr=subprocess.STDOUT)
        return p

    def wait_with_timeout(self, proc, timeout=10):
        for _ in range(timeout):
            x = proc.poll()
            if x is None:
                time.sleep(1)
            else:
                return x

        os.kill(proc.pid, signal.SIGKILL)
        return proc.wait()

    def run_script(self, name):
        path = os.path.join(
            self.plugin_dir, f"dist/BasicPlugin.bundle/Contents/MacOS/{name}"
        )

        p = subprocess.Popen(
            [path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            close_fds=False,
        )
        # stderr=subprocess.STDOUT)
        return p

    #
    # End of setup code
    #

    def test_helper1(self):
        p = self.run_script("helper1")
        lines = p.communicate()[0]
        p.wait()

        self.assertEqual(lines, b"Helper 1\n")

    def test_helper2(self):
        p = self.run_script("helper2")
        lines = p.communicate()[0]
        p.wait()

        self.assertEqual(lines, b"Helper 2\n")

    def test_basic_start(self):
        p = self.start_app()
        v = p.stdout.readline()

        self.assertFalse(v.startswith(b"** Cannot load bundle"))

        p.stdin.write(b"BasicPlugin.bundle:test startup\n")
        p.stdin.flush()

        v = p.stdout.readline()
        self.assertEqual(v.strip(), b"+ test startup")

        p.stdin.close()
        p.stdout.close()

        status = self.wait_with_timeout(p)
        self.assertEqual(status, 0)


class TestBasicAliasPlugin(TestBasicPlugin):
    py2app_args = ["--alias"]


class TestBasicSemiStandalonePlugin(TestBasicPlugin):
    py2app_args = ["--semi-standalone"]


class TestBasicPluginUnicodePath(TestBasicPlugin):
    plugin_dir = os.path.join(DIR_NAME, "basic_plugin " + chr(2744))

    @classmethod
    def setUpClass(cls):
        kill_child_processes()

        try:
            if os.path.exists(cls.plugin_dir):
                shutil.rmtree(cls.plugin_dir)

            assert not os.path.exists(cls.plugin_dir)
            shutil.copytree(TestBasicPlugin.plugin_dir, cls.plugin_dir)

            super().setUpClass()

        except:  # noqa: E722, B001
            if os.path.exists(cls.plugin_dir):
                shutil.rmtree(cls.plugin_dir)
            raise

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.plugin_dir):
            shutil.rmtree(cls.plugin_dir)

        super().tearDownClass()


class TestBasicAliasPluginUnicodePath(TestBasicPluginUnicodePath):
    py2app_args = ["--alias"]


class TestBasicSemiStandalonePluginUnicodePath(TestBasicPluginUnicodePath):
    py2app_args = ["--semi-standalone"]


if __name__ == "__main__":
    unittest.main()
