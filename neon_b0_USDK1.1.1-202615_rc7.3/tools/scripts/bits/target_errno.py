##########################################################################
# Copyright [2025] [InnoPhase IoT Inc.]
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
##########################################################################

import enum

class TargetErrno(enum.IntEnum):
    EPERM                = 1    # Operation not permitted
    ENOENT               = 2    # No such file or directory
    ESRCH                = 3    # No such process
    EINTR                = 4    # Interrupted system call
    EIO                  = 5    # Input/output error
    ENXIO                = 6    # Device not configured
    E2BIG                = 7    # Argument list too long
    ENOEXEC              = 8    # Exec format error
    EBADF                = 9    # Bad file descriptor
    ECHILD               = 10   # No child processes
    EDEADLK              = 11   # Resource deadlock avoided
    ENOMEM               = 12   # Cannot allocate memory
    EACCES               = 13   # Permission denied
    EFAULT               = 14   # Bad address
    ENOTBLK              = 15   # Block device required
    EBUSY                = 16   # Device busy
    EEXIST               = 17   # File exists
    EXDEV                = 18   # Cross-device link
    ENODEV               = 19   # Operation not supported by device
    ENOTDIR              = 20   # Not a directory
    EISDIR               = 21   # Is a directory
    EINVAL               = 22   # Invalid argument
    ENFILE               = 23   # Too many open files in system
    EMFILE               = 24   # Too many open files
    ENOTTY               = 25   # Inappropriate ioctl for device
    ETXTBSY              = 26   # Text file busy
    EFBIG                = 27   # File too large
    ENOSPC               = 28   # No space left on device
    ESPIPE               = 29   # Illegal seek
    EROFS                = 30   # Read-only file system
    EMLINK               = 31   # Too many links
    EPIPE                = 32   # Broken pipe
    EDOM                 = 33   # Numerical argument out of domain
    ERANGE               = 34   # Result too large or too small
    EAGAIN               = 35   # Resource temporarily unavailable
    EINPROGRESS          = 36   # Operation now in progress
    EALREADY             = 37   # Operation already in progress
    ENOTSOCK             = 38   # Socket operation on non-socket
    EDESTADDRREQ         = 39   # Destination address required
    EMSGSIZE             = 40   # Message too long
    EPROTOTYPE           = 41   # Protocol wrong type for socket
    ENOPROTOOPT          = 42   # Protocol option not available
    EPROTONOSUPPORT      = 43   # Protocol not supported
    EOPNOTSUPP           = 45   # Operation not supported
    EAFNOSUPPORT         = 47   # Address family not supported by protocol family
    EADDRINUSE           = 48   # Address already in use
    EADDRNOTAVAIL        = 49   # Can't assign requested address
    ENETDOWN             = 50   # Network is down
    ENETUNREACH          = 51   # Network is unreachable
    ENETRESET            = 52   # Network dropped connection on reset
    ECONNABORTED         = 53   # Software caused connection abort
    ECONNRESET           = 54   # Connection reset by peer
    ENOBUFS              = 55   # No buffer space available
    EISCONN              = 56   # Socket is already connected
    ENOTCONN             = 57   # Socket is not connected
    ETIMEDOUT            = 60   # Operation timed out
    ECONNREFUSED         = 61   # Connection refused
    ELOOP                = 62   # Too many levels of symbolic links
    ENAMETOOLONG         = 63   # File name too long
    EHOSTUNREACH         = 65   # No route to host
    ENOTEMPTY            = 66   # Directory not empty
    EDQUOT               = 69   # Disc quota exceeded
    ESTALE               = 70   # Stale NFS file handle
    ENOLCK               = 77   # No locks available
    ENOSYS               = 78   # Function not implemented
    EIDRM                = 82   # Identifier removed
    ENOMSG               = 83   # No message of desired type
    EOVERFLOW            = 84   # Value too large to be stored in data type
    EILSEQ               = 85   # Illegal byte sequence
    ENOTSUP              = 86   # Not supported
    ECANCELED            = 87   # Operation canceled
    EBADMSG              = 88   # Bad or Corrupt message
    ENODATA              = 89   # No message available
    ENOSR                = 90   # No STREAM resources
    ENOSTR               = 91   # Not a STREAM
    ETIME                = 92   # STREAM ioctl timeout
    EMULTIHOP            = 94   # Multihop attempted
    ENOLINK              = 95   # Link has been severed
    EPROTO               = 96   # Protocol error
    EOWNERDEAD           = 97   # Previous owner died
    ENOTRECOVERABLE      = 98   # State not recoverable

def target_strerror(errno):
    errstrtable = {
        TargetErrno.EPERM:            'Operation not permitted',
        TargetErrno.ENOENT:           'No such file or directory',
        TargetErrno.ESRCH:            'No such process',
        TargetErrno.EINTR:            'Interrupted system call',
        TargetErrno.EIO:              'Input/output error',
        TargetErrno.ENXIO:            'Device not configured',
        TargetErrno.E2BIG:            'Argument list too long',
        TargetErrno.ENOEXEC:          'Exec format error',
        TargetErrno.EBADF:            'Bad file descriptor',
        TargetErrno.ECHILD:           'No child processes',
        TargetErrno.EDEADLK:          'Resource deadlock avoided',
        TargetErrno.ENOMEM:           'Cannot allocate memory',
        TargetErrno.EACCES:           'Permission denied',
        TargetErrno.EFAULT:           'Bad address',
        TargetErrno.ENOTBLK:          'Block device required',
        TargetErrno.EBUSY:            'Device busy',
        TargetErrno.EEXIST:           'File exists',
        TargetErrno.EXDEV:            'Cross-device link',
        TargetErrno.ENODEV:           'Operation not supported by device',
        TargetErrno.ENOTDIR:          'Not a directory',
        TargetErrno.EISDIR:           'Is a directory',
        TargetErrno.EINVAL:           'Invalid argument',
        TargetErrno.ENFILE:           'Too many open files in system',
        TargetErrno.EMFILE:           'Too many open files',
        TargetErrno.ENOTTY:           'Inappropriate ioctl for device',
        TargetErrno.ETXTBSY:          'Text file busy',
        TargetErrno.EFBIG:            'File too large',
        TargetErrno.ENOSPC:           'No space left on device',
        TargetErrno.ESPIPE:           'Illegal seek',
        TargetErrno.EROFS:            'Read-only file system',
        TargetErrno.EMLINK:           'Too many links',
        TargetErrno.EPIPE:            'Broken pipe',
        TargetErrno.EDOM:             'Numerical argument out of domain',
        TargetErrno.ERANGE:           'Result too large or too small',
        TargetErrno.EAGAIN:           'Resource temporarily unavailable',
        TargetErrno.EINPROGRESS:      'Operation now in progress',
        TargetErrno.EALREADY:         'Operation already in progress',
        TargetErrno.ENOTSOCK:         'Socket operation on non-socket',
        TargetErrno.EDESTADDRREQ:     'Destination address required',
        TargetErrno.EMSGSIZE:         'Message too long',
        TargetErrno.EPROTOTYPE:       'Protocol wrong type for socket',
        TargetErrno.ENOPROTOOPT:      'Protocol option not available',
        TargetErrno.EPROTONOSUPPORT:  'Protocol not supported',
        TargetErrno.EOPNOTSUPP:       'Operation not supported',
        TargetErrno.EAFNOSUPPORT:     'Address family not supported by protocol family',
        TargetErrno.EADDRINUSE:       'Address already in use',
        TargetErrno.EADDRNOTAVAIL:    "Can't assign requested address",
        TargetErrno.ENETDOWN:         'Network is down',
        TargetErrno.ENETUNREACH:      'Network is unreachable',
        TargetErrno.ENETRESET:        'Network dropped connection on reset',
        TargetErrno.ECONNABORTED:     'Software caused connection abort',
        TargetErrno.ECONNRESET:       'Connection reset by peer',
        TargetErrno.ENOBUFS:          'No buffer space available',
        TargetErrno.EISCONN:          'Socket is already connected',
        TargetErrno.ENOTCONN:         'Socket is not connected',
        TargetErrno.ETIMEDOUT:        'Operation timed out',
        TargetErrno.ECONNREFUSED:     'Connection refused',
        TargetErrno.ELOOP:            'Too many levels of symbolic links',
        TargetErrno.ENAMETOOLONG:     'File name too long',
        TargetErrno.EHOSTUNREACH:     'No route to host',
        TargetErrno.ENOTEMPTY:        'Directory not empty',
        TargetErrno.EDQUOT:           'Disc quota exceeded',
        TargetErrno.ESTALE:           'Stale NFS file handle',
        TargetErrno.ENOLCK:           'No locks available',
        TargetErrno.ENOSYS:           'Function not implemented',
        TargetErrno.EIDRM:            'Identifier removed',
        TargetErrno.ENOMSG:           'No message of desired type',
        TargetErrno.EOVERFLOW:        'Value too large to be stored in data type',
        TargetErrno.EILSEQ:           'Illegal byte sequence',
        TargetErrno.ENOTSUP:          'Not supported',
        TargetErrno.ECANCELED:        'Operation canceled',
        TargetErrno.EBADMSG:          'Bad or Corrupt message',
        TargetErrno.ENODATA:          'No message available',
        TargetErrno.ENOSR:            'No STREAM resources',
        TargetErrno.ENOSTR:           'Not a STREAM',
        TargetErrno.ETIME:            'STREAM ioctl timeout',
        TargetErrno.EMULTIHOP:        'Multihop attempted',
        TargetErrno.ENOLINK:          'Link has been severed',
        TargetErrno.EPROTO:           'Protocol error'
    }
    return errstrtable.get(errno, f'unknown error {errno}')
