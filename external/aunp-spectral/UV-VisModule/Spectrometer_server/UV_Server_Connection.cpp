// UV_Server_Connection.cpp : This file contains the 'main' function. Program execution begins and ends there.
//

#include <iostream>
#include <string>
#include "TCPServer.h"
#include "JSONWriter.h"


using namespace std;
string serverIP = "127.0.0.1";
int port = 54011;


int main() {

	TCPServer server(serverIP, port);

	if (server.initWinsock())
		server.run();
}