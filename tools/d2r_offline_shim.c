#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <netdb.h>
#include <netinet/in.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/types.h>

static int is_local_or_lan_ipv4(uint32_t ip) {
    if (ip == 0) return 1;                          /* 0.0.0.0 */
    if ((ip >> 24) == 127) return 1;                /* 127.0.0.0/8 loopback */
    if ((ip >> 24) == 10) return 1;                 /* 10.0.0.0/8 LAN */
    if ((ip >> 20) == ((172 << 4) | 1)) return 1;   /* 172.16.0.0/12 LAN */
    if ((ip >> 16) == ((192 << 8) | 168)) return 1; /* 192.168.0.0/16 LAN */
    return 0;
}

static int is_local_node(const char *node) {
    if (!node || !node[0]) return 1;
    if (strcmp(node, "localhost") == 0) return 1;
    if (strncmp(node, "127.", 4) == 0) return 1;
    if (strncmp(node, "192.168.", 8) == 0) return 1;
    if (strncmp(node, "10.", 3) == 0) return 1;
    if (strncmp(node, "172.", 4) == 0) return 1;
    if (strcmp(node, "0.0.0.0") == 0) return 1;
    if (strcmp(node, "::1") == 0) return 1;
    if (strcmp(node, "::") == 0) return 1;
    return 0;
}

int getaddrinfo(const char *node, const char *service,
                const struct addrinfo *hints, struct addrinfo **res) {
    if (!is_local_node(node)) {
        return EAI_NONAME;
    }
    int (*real_getaddrinfo)(const char *, const char *,
                            const struct addrinfo *, struct addrinfo **) =
        dlsym(RTLD_NEXT, "getaddrinfo");
    return real_getaddrinfo(node, service, hints, res);
}

int connect(int sockfd, const struct sockaddr *addr, socklen_t addrlen) {
    if (addr) {
        if (addr->sa_family == AF_INET && addrlen >= sizeof(struct sockaddr_in)) {
            const struct sockaddr_in *sin = (const struct sockaddr_in *)addr;
            uint32_t ip = ntohl(sin->sin_addr.s_addr);
            if (!is_local_or_lan_ipv4(ip)) {
                errno = ENETUNREACH;
                return -1;
            }
        } else if (addr->sa_family == AF_INET6 && addrlen >= sizeof(struct sockaddr_in6)) {
            const struct sockaddr_in6 *sin6 = (const struct sockaddr_in6 *)addr;
            if (!IN6_IS_ADDR_LOOPBACK(&sin6->sin6_addr) &&
                !IN6_IS_ADDR_UNSPECIFIED(&sin6->sin6_addr)) {
                errno = ENETUNREACH;
                return -1;
            }
        }
    }
    int (*real_connect)(int, const struct sockaddr *, socklen_t) =
        dlsym(RTLD_NEXT, "connect");
    return real_connect(sockfd, addr, addrlen);
}
