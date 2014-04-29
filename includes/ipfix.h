#ifndef FLOW_IPFIX_H_
#define FLOW_IPFIX_H_

#define PACKED __attribute__((__packed__))

#define IPV5_VERSION  5

typedef struct PACKED ipv5_header {
	uint16_t version;			// NetFlow export format version number
	uint16_t count;				// Number of flows exported in this packet (1-30)
	uint32_t sys_uptime;		// Current time in milliseconds since the export device booted
	uint32_t unix_secs;			// Current count of seconds since 0000 UTC 1970
	uint32_t unix_nsecs;		// Residual nanoseconds since 0000 UTC 1970
	uint32_t flow_sequence;		// Sequence counter of total flows seen
	uint8_t  engine_type;		// Type of flow-switching engine
	uint8_t  engine_id;			// Slot number of the flow-switching engine
	uint16_t sampling_interval; // First two bits hold the sampling mode; remaining 14 bits hold value of sampling interval
} ipv5_header_t;

typedef struct PACKED ipv5_flow {
	uint32_t srcaddr; 			// Source IP address
	uint32_t dstaddr;			// Destination IP address
	uint32_t nexthop; 			// IP address of next hop router
	uint16_t input;				// SNMP index of input interface
	uint16_t output;			// SNMP index of output interface
	uint32_t dPkts;				// Packets in the flow
	uint32_t dOctets;			// Total number of Layer 3 bytes in the packets of the flow
	uint32_t first;				// SysUptime at start of flow
	uint32_t last;				// SysUptime at the time the last packet of the flow was received
	uint16_t srcport;			// TCP/UDP source port number or equivalent
	uint16_t dstport;			// TCP/UDP destination port number or equivalent
	uint8_t  pad1;				// Unused (zero) bytes
	uint8_t  tcp_flags;			// Cumulative OR of TCP flags
	uint8_t  prot;				// IP protocol type (for example, TCP = 6; UDP = 17)
	uint8_t  tos;				// IP type of service (ToS)
	uint16_t src_as;			// Autonomous system number of the source, either origin or peer
	uint16_t dst_as;			// Autonomous system number of the destination, either origin or peer
	uint8_t  src_mask;			// Source address prefix mask bits
	uint8_t  dst_mask;			// Destination address prefix mask bits
	uint16_t pad2;				// Unused (zero) bytes
} ipv5_flow_t;

typedef struct PACKED flow_info flow_info_t;

struct PACKED flow_info {
	flow_info_t*		next;
	uint64_t 			flowpacks;
	uint64_t 			packets;
	uint64_t 			octets;
	uint64_t 			flows;
	uint32_t			used;
};

typedef struct PACKED flow_collection {
	flow_info_t			info;
	uint32_t 			minaddr;
	uint32_t 			maxaddr;
} flow_collection_t;

typedef struct PACKED flow_entry flow_entry_t;

typedef struct PACKED flow_destination flow_destination_t;

struct PACKED flow_entry {
	flow_entry_t*		next;
	flow_entry_t*		first;
	flow_destination_t* destaddr;
	flow_collection_t	coll;
};

struct PACKED flow_destination {
	flow_info_t			info;
	struct sockaddr_in 	addr;
};

struct PACKED flow_source {
	uint32_t 			address;
	uint32_t			activity;
	uint64_t			total;
	uint32_t			inactive;
	uint32_t 			seq;
	uint64_t			ooscount;
} flow_source_t;

struct PACKED flow_counters {
	uint64_t 			all;
	uint64_t			broken;
	uint64_t			dropped;
	uint64_t			other;
} flow_counters_t;

#include <sys/types.h>
#include <sys/socket.h>

int mkaddr(const char* ip, uint16_t port, struct sockaddr_in* addr);
int sendflow(int sfd, const char* buffer, int size, const struct sockaddr_in* addr);

#endif /* FLOW_IPFIX_H_ */
