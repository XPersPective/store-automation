"""Reused native process containment from the previous factory.
Windows kill-on-close jobs; POSIX process group cleanup is not a parent-death
sandbox. This module starts bounded local checks, not autonomous writers.
"""
import ctypes
import os
import subprocess
import time
import uuid


class ContainmentError(RuntimeError):
    """Do not replace the owner until termination has been reconciled."""


class ProcessTree:
    """Contain descendants before the first instruction of a Windows child."""
    def __init__(self, name=None, existing=False):
        self.name = name or 'store-' + uuid.uuid4().hex
        self.job = None
        self.proc = None
        if os.name != 'nt':
            return
        from ctypes import wintypes as w
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        k = self.kernel
        signatures = {
            'CreateJobObjectW': ([ctypes.c_void_p, w.LPCWSTR], w.HANDLE),
            'OpenJobObjectW': ([w.DWORD, w.BOOL, w.LPCWSTR], w.HANDLE),
            'SetInformationJobObject': ([w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD], w.BOOL),
            'QueryInformationJobObject': ([w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD, ctypes.c_void_p], w.BOOL),
            'AssignProcessToJobObject': ([w.HANDLE, w.HANDLE], w.BOOL),
            'TerminateJobObject': ([w.HANDLE, w.UINT], w.BOOL),
            'CloseHandle': ([w.HANDLE], w.BOOL),
            'OpenProcess': ([w.DWORD, w.BOOL, w.DWORD], w.HANDLE),
            'GetCurrentProcess': ([], w.HANDLE),
            'DuplicateHandle': ([w.HANDLE, w.HANDLE, w.HANDLE, ctypes.POINTER(w.HANDLE), w.DWORD, w.BOOL, w.DWORD], w.BOOL),
            'CreateToolhelp32Snapshot': ([w.DWORD, w.DWORD], w.HANDLE),
            'Thread32First': ([w.HANDLE, ctypes.c_void_p], w.BOOL),
            'Thread32Next': ([w.HANDLE, ctypes.c_void_p], w.BOOL),
            'OpenThread': ([w.DWORD, w.BOOL, w.DWORD], w.HANDLE),
            'ResumeThread': ([w.HANDLE], w.DWORD),
            'IsProcessInJob': ([w.HANDLE, w.HANDLE, ctypes.POINTER(w.BOOL)], w.BOOL),
        }
        for name_, (args, result) in signatures.items():
            function = getattr(k, name_)
            function.argtypes, function.restype = args, result
        self.job = k.OpenJobObjectW(12, False, self.name) if existing else k.CreateJobObjectW(None, self.name)
        if not self.job:
            raise OSError('Owned process-tree containment unavailable')
        if not existing:
            class Basic(ctypes.Structure):
                _fields_ = [('user', ctypes.c_longlong), ('job', ctypes.c_longlong), ('flags', w.DWORD),
                            ('min_working', ctypes.c_size_t), ('max_working', ctypes.c_size_t),
                            ('active', w.DWORD), ('affinity', ctypes.c_size_t), ('priority', w.DWORD), ('scheduling', w.DWORD)]
            class Extended(ctypes.Structure):
                _fields_ = [('basic', Basic), ('io', ctypes.c_ulonglong * 6),
                            ('memory', ctypes.c_size_t * 4)]
            limits = Extended()
            limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE; no breakaway.
            if not k.SetInformationJobObject(self.job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
                k.CloseHandle(self.job)
                self.job = None
                raise OSError('Cannot enforce process-tree containment')

    def spawn(self, argv, **kwargs):
        before_resume = kwargs.pop('before_resume', None)
        if os.name != 'nt':
            self.proc = subprocess.Popen(argv, start_new_session=True, **kwargs)
            if before_resume:
                before_resume(self.proc)
            return self.proc
        from ctypes import wintypes as w
        k = self.kernel
        kwargs['creationflags'] = kwargs.get('creationflags', 0) | 4  # CREATE_SUSPENDED.
        self.proc = subprocess.Popen(argv, **kwargs)
        process = k.OpenProcess(0x1141, False, self.proc.pid)
        try:
            if not process or not k.AssignProcessToJobObject(self.job, process):
                raise OSError(ctypes.get_last_error(), 'Cannot assign suspended process to owned job')
            if before_resume:
                before_resume(self.proc)
            class ThreadEntry(ctypes.Structure):
                _fields_ = [('size', w.DWORD), ('usage', w.DWORD), ('thread', w.DWORD),
                            ('owner', w.DWORD), ('base', w.LONG), ('delta', w.LONG), ('flags', w.DWORD)]
            snapshot = k.CreateToolhelp32Snapshot(4, 0)
            if snapshot == ctypes.c_void_p(-1).value:
                raise OSError('Cannot inspect suspended process thread')
            threads = []
            try:
                entry = ThreadEntry()
                entry.size = ctypes.sizeof(entry)
                more = k.Thread32First(snapshot, ctypes.byref(entry))
                while more:
                    if entry.owner == self.proc.pid:
                        threads.append(entry.thread)
                    more = k.Thread32Next(snapshot, ctypes.byref(entry))
            finally:
                k.CloseHandle(snapshot)
            if len(threads) != 1:
                raise OSError('Unexpected suspended process threads; refusing execution')
            thread = k.OpenThread(2, False, threads[0])
            try:
                if not thread or k.ResumeThread(thread) != 1:
                    raise OSError('Cannot resume contained process')
            finally:
                if thread:
                    k.CloseHandle(thread)
            return self.proc
        except BaseException:
            self.proc.kill()
            self.proc.wait(timeout=5)
            self.close()
            for pipe in (self.proc.stdin, self.proc.stdout, self.proc.stderr):
                if pipe:
                    pipe.close()
            raise
        finally:
            if process:
                k.CloseHandle(process)

    def close(self):
        try:
            self._close()
        except (OSError, RuntimeError) as error:
            raise ContainmentError('Owned process-tree termination is unverified; preserve dispatch lock') from error

    def _close(self):
        if os.name == 'nt' and self.job:
            from ctypes import wintypes as w
            k = self.kernel
            if not k.TerminateJobObject(self.job, 1):
                raise OSError('Cannot terminate owned process tree; reconciliation required')
            class Accounting(ctypes.Structure):
                _fields_ = [('times', ctypes.c_longlong * 4), ('faults', w.DWORD),
                            ('total', w.DWORD), ('active', w.DWORD), ('terminated', w.DWORD)]
            accounting = Accounting()
            for _ in range(50):
                if not k.QueryInformationJobObject(self.job, 1, ctypes.byref(accounting), ctypes.sizeof(accounting), None):
                    raise OSError('Cannot verify owned process-tree termination')
                if accounting.active == 0:
                    k.CloseHandle(self.job)
                    self.job = None
                    return
                time.sleep(.1)
            raise RuntimeError('Owned descendants remain; reconciliation required')
        elif os.name != 'nt' and self.proc:
            import signal
            try:
                os.killpg(self.proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            self.proc = None
