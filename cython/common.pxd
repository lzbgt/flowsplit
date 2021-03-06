
cdef extern from "stdint.h":
    ctypedef long uint8_t
    ctypedef long uint16_t
    ctypedef long uint32_t
    ctypedef long uint64_t

cdef extern from "linux/ip.h":
    cdef struct iphdr:
        long saddr
        long daddr
        
cdef extern from "linux/udp.h":
    cdef struct udphdr:
        int source
        int dest
        int check

cdef extern from "netinet/in.h":
    int ntohs (int __netshort) nogil
    long ntohl (long __netlong) nogil
    uint16_t htons (uint16_t __hostshort) nogil
    uint32_t htonl(uint32_t hostlong) nogil

    cdef struct in_addr:
        long s_addr

    cdef struct sockaddr_in:
        int sin_family
        int sin_port
        in_addr sin_addr

cdef extern:
    int _import_array()
    int _import_umath()

cdef extern from "sys/socket.h":
    cdef int AF_INET
    ctypedef long socklen_t 
    ssize_t sendto (int __fd, const void *__buf, size_t __n,
                   int __flags, const sockaddr_in* __addr, size_t __addr_len) nogil
    ssize_t recvfrom(int sockfd, void *buf, size_t len, int flags,
                     sockaddr_in *src_addr, socklen_t *addrlen) nogil                   

cdef extern from "arpa/inet.h":
    int inet_aton (const char *__cp, in_addr *__inp) nogil

cdef extern from "string.h" nogil:
    void *memset(void *s, int c, size_t n) nogil
    int memcmp (const void *A1, const void *A2, size_t SIZE) nogil
    void *memcpy(void *restrict, const void *restrict, size_t) nogil

cdef extern from "ipfix.h":
    cdef int IPV5_VERSION
    
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
        
    cdef struct flow_info:
        flow_info*  next
        long        flowpacks
        long        packets
        long        octets
        long        flows
        long        used
        
    cdef struct flow_collection:
        flow_info    info
        long         minaddr
        long         maxaddr

    cdef struct flow_destination:
        flow_info    info
        sockaddr_in  addr

    cdef struct flow_entry:    
        flow_entry*         next
        flow_entry*         first
        flow_destination*   destaddr
        flow_collection     coll
        
    cdef struct flow_source:
        long        address
        long        activity
        long        total
        int         inactive
        long        seq
        long        ooscount

    cdef struct flow_counters:
        long        all
        long        broken
        long        dropped
        long        other
