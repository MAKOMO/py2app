"""
Test case for building an app bundle with a command-line tool, that bundle
is than queried in the various test methods to check if the app bundle
is correct.

This is basicly a black-box functional test of the core py2app functionality

The app itself:
    - main script has 'if 0: import modules'
    - main script has a loop that reads and exec-s statements
    - the 'modules' module depends on a set of modules/packages through
      various forms of imports (absolute, relative, old-style python2,
      namespace packages 'pip-style', namespace package other,
      zipped eggs and non-zipped eggs, develop eggs)
    - add another test that does something simular, using virtualenv to
      manage a python installation
"""
import sys
if (sys.version_info[0] == 2 and sys.version_info[:2] >= (2,7)) or \
        (sys.version_info[0] == 3 and sys.version_info[:2] >= (3,2)):
    import unittest
else:
    import unittest2 as unittest

import subprocess
import shutil
import time
import os
import signal

DIR_NAME=os.path.dirname(os.path.abspath(__file__))

if sys.version_info[0] == 2:
    def B(value):
        return value

else:
    def B(value):
        return value.encode('latin1')




class TestBasicApp (unittest.TestCase):
    py2app_args = []

    # Basic setup code
    #
    # The code in this block needs to be moved to
    # a base-class.
    @classmethod
    def setUpClass(cls):
        p = subprocess.Popen([
                sys.executable,
                    'setup.py', 'py2app'] + cls.py2app_args,
            cwd = os.path.join(DIR_NAME, 'basic_app'),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            close_fds=True)
        lines = p.communicate()[0]
        if p.wait() != 0:
            print (lines)
            raise AssertionError("Creating basic_app bundle failed")

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(os.path.join(DIR_NAME, 'basic_app/build')):
            shutil.rmtree(os.path.join(DIR_NAME, 'basic_app/build'))

        if os.path.exists(os.path.join(DIR_NAME, 'basic_app/dist')):
            shutil.rmtree(os.path.join(DIR_NAME, 'basic_app/dist'))

    def start_app(self):
        # Start the test app, return a subprocess object where
        # stdin and stdout are connected to pipes.
        path = os.path.join(
                DIR_NAME,
            'basic_app/dist/BasicApp.app/Contents/MacOS/BasicApp')

        p = subprocess.Popen([path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                close_fds=True,
                )
                #stderr=subprocess.STDOUT)
        return p

    def wait_with_timeout(self, proc, timeout=10):
        for i in range(timeout):
            x = proc.poll()
            if x is None:
                time.sleep(1)
            else:
                return x

        os.kill(proc.pid, signal.SIGKILL)
        return proc.wait()

    #
    # End of setup code
    # 

    def test_basic_start(self):
        p = self.start_app()

        p.stdin.close()

        exit = self.wait_with_timeout(p)
        self.assertEqual(exit, 0)

        p.stdout.close()

    def test_simple_imports(self):
        p = self.start_app()

        # Basic module that is always present:
        p.stdin.write('import_module("os")\n'.encode('latin1'))
        p.stdin.flush()
        ln = p.stdout.readline()
        self.assertEqual(ln.strip(), B("os"))

        # Dependency of the main module:
        p.stdin.write('import_module("decimal")\n'.encode('latin1'))
        p.stdin.flush()
        ln = p.stdout.readline()
        self.assertEqual(ln.strip(), B("decimal"))

        if '--alias' not in self.py2app_args:
            # Not a dependency of the module (stdlib):
            p.stdin.write('import_module("xmllib")\n'.encode('latin1'))
            p.stdin.flush()
            ln = p.stdout.readline().decode('utf-8')
            self.assertTrue(ln.strip().startswith("* import failed"), ln)

        # Not a dependency of the module (external):
        p.stdin.write('import_module("py2app")\n'.encode('latin1'))
        p.stdin.flush()
        ln = p.stdout.readline().decode('utf-8')
        self.assertTrue(ln.strip().startswith("* import failed"), ln)

        p.stdin.close()
        p.stdout.close()

class TestBasicAliasApp (TestBasicApp):
    py2app_args = [ '--alias', ]

if __name__ == "__main__":
    unittest.main()
