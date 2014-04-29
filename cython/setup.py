'''
Created on Jun 27, 2013

@author: schernikov
'''
import numpy as np
from distutils.core import setup, Extension
from Cython.Build import cythonize
from Cython.Distutils import build_ext

ext_modules = cythonize(["nreceiver.pyx", 'ntester.pyx'], extra_compile_args=['-DNPY_NO_DEPRECATION_WARNING'])

#ext_modules.extend([Extension('minutescoll',
#                             sources=['../csrc/minutescoll.c'], 
#                             include_dirs=['../includes']),
#                    Extension('hourscoll',
#                             sources=['../csrc/hourscoll.c'], 
#                             include_dirs=['../includes']),
#                    Extension('dayscoll',
#                             sources=['../csrc/dayscoll.c'], 
#                             include_dirs=['../includes'])])

res = setup(ext_modules = ext_modules,
            #cmdclass = {'build_ext': cpp_build_ext},
            script_args=['build_ext', '--inplace'], include_dirs=[np.get_include()])
