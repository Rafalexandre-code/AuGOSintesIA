#pragma once

#include <string>
#include <WS2tcpip.h>
#pragma comment (lib, "ws2_32.lib")

using namespace std;

class TCPServer;

//Callback fct = fct with fct as parameter.
typedef void(*MessageReceivedHandler)(TCPServer* listener, int socketID, string msg);

class TCPServer {
public:
	TCPServer(string ipAddress, int port);
	~TCPServer();

	void sendMsg(int clientSocket, string msg);
	bool initWinsock();
	void run();
	void cleanupWinsock();
	double** callRawUV(bool entrance);
	double* callTargetUV(double** rawData);
	string date_time(tm* local_time);

private:
	SOCKET createSocket();
	std::string listenerIPAddress;
	int listenerPort;
	//MessageReceivedHandler messageReceived; 
};
