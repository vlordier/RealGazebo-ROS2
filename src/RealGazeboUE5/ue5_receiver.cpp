/**
 * RealGazebo UDP Receiver — standalone mock for the UE5 ARxUdp actor.
 *
 * Listens on UDP port 5005 (default), parses the 31-byte packets
 * sent by libRealGazebo.so, and prints decoded vehicle poses.
 *
 * Packet format (matches C++ struct RealGazeboPacket):
 *   <BBB  — header: vehicle_code, vehicle_num, packet_type
 *   + 7 floats — x, y, z, qw, qx, qy, qz
 *   = 3 + 28 = 31 bytes
 *
 * Build: g++ -std=c++17 -o ue5_receiver ue5_receiver.cpp
 * Usage: ./ue5_receiver [port]
 */

#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

#include <cstring>
#include <iostream>
#include <tuple>

#pragma pack(push, 1)
struct RealGazeboPacket {
    uint8_t vehicle_code;
    uint8_t vehicle_num;
    uint8_t packet_type;
    float x, y, z, qw, qx, qy, qz;
};
#pragma pack(pop)

static_assert(sizeof(RealGazeboPacket) == 31,
              "RealGazeboPacket must be 31 bytes");

int main(int argc, char* argv[]) {
    int port = (argc > 1) ? std::atoi(argv[1]) : 5005;

    int sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock < 0) {
        std::cerr << "Failed to create socket" << std::endl;
        return 1;
    }

    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = INADDR_ANY;
    addr.sin_port = htons(port);

    if (bind(sock, (sockaddr*)&addr, sizeof(addr)) < 0) {
        std::cerr << "Failed to bind to port " << port << std::endl;
        close(sock);
        return 1;
    }

    std::cout << "RealGazebo UDP receiver listening on port " << port << std::endl;
    std::cout << "Packet size: " << sizeof(RealGazeboPacket) << " bytes" << std::endl;
    std::cout << "Waiting for data from libRealGazebo.so..." << std::endl;
    std::cout << std::endl;

    while (true) {
        RealGazeboPacket pkt{};
        sockaddr_in sender{};
        socklen_t sender_len = sizeof(sender);

        ssize_t n = recvfrom(sock, &pkt, sizeof(pkt), 0,
                             (sockaddr*)&sender, &sender_len);
        if (n < 0) {
            std::cerr << "recvfrom failed" << std::endl;
            continue;
        }

        char sender_ip[INET_ADDRSTRLEN];
        inet_ntop(AF_INET, &sender.sin_addr, sender_ip, sizeof(sender_ip));

        std::cout << "[" << sender_ip << ":" << ntohs(sender.sin_port) << "] "
                  << "vehicle=" << (int)pkt.vehicle_num
                  << " code=" << (int)pkt.vehicle_code
                  << " type=" << (int)pkt.packet_type
                  << " pos=(" << pkt.x << ", " << pkt.y << ", " << pkt.z << ")"
                  << " quat=(" << pkt.qw << ", " << pkt.qx << ", " << pkt.qy
                  << ", " << pkt.qz << ")"
                  << " (" << n << " bytes)" << std::endl;
    }

    close(sock);
    return 0;
}
