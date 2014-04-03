
cdef extern from "stdint.h":
    ctypedef long uint8_t
    ctypedef long uint16_t
    ctypedef long uint32_t
    ctypedef long uint64_t

cdef extern from "netinet/in.h":
    int ntohs (int __netshort) nogil
    long ntohl (long __netlong) nogil
    uint16_t htons (uint16_t __hostshort) nogil

    cdef struct in_addr:
        pass

    cdef struct sockaddr_in:
        int sin_family
        int sin_port
        in_addr sin_addr

cdef extern from "sys/socket.h":
    cdef int AF_INET
    ssize_t sendto (int __fd, const void *__buf, size_t __n,
                   int __flags, const sockaddr_in* __addr, size_t __addr_len) nogil

cdef extern from "arpa/inet.h":
    int inet_aton (const char *__cp, in_addr *__inp) nogil

cdef extern from "string.h" nogil:
    void *memset(void *s, int c, size_t n) nogil
    int memcmp (const void *A1, const void *A2, size_t SIZE) nogil
    void *memcpy(void *restrict, const void *restrict, size_t) nogil

cdef extern from "ipfix.h":

    cdef struct ipv5_header:
        int version
        int count
        long sys_uptime
        long unix_secs
        long unix_nsecs
        long flow_sequence
        int engine_type
        int engine_id
        int sampling_interval

    cdef struct ipv5_flow:
        long srcaddr
        long dstaddr
        long nexthop
        int input
        int output
        long dPkts
        long dOctets
        long first
        long last
        int srcport
        int dstport
        int pad1
        int tcp_flags
        int prot
        int tos
        int src_as
        int dst_as
        int src_mask
        int dst_mask
        int pad2
        
    cdef struct flow_collection:
        long         minaddr
        long         maxaddr
        long         packets
        long         octets
        long         flows

    cdef struct flow_destination:
        sockaddr_in         addr
        long                flowpacks
        long                used
        flow_destination*   next
    
    cdef struct flow_entry:    
        flow_entry*         next
        flow_entry*         first
        flow_destination*   destaddr
        flow_collection     coll

