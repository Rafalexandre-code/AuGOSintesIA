#pragma warning(disable : 4996)

#define WIN32

// Basic Library
#include <iostream>
#include "TCPServer.h"
#include <string>
#include <sstream>
#include <vector>
#include <ctime>
#include "JSONWriter.h"
#include <conio.h>
#include <iostream>
#include <fstream>
#include <typeinfo>
#include <algorithm>
#include "TCPServer.h"
// OmniDrivier Library
#include "Wrapper.h"
// Spam Library
#include "AdvancedPeakFinding.h"
#include "SpectralMath.h"
#include "SpectrumPeak.h"
#include "CoreAbsorbance.h"

using namespace std;
const int MAX_BUFFER_SIZE = 4096;			//Constant value for the buffer size = where we will store the data received.

// send string (windows to ubuntu)
// parse our string (in ubuntu)
// save our data using any kind of file format (such as json, csv...)

TCPServer::TCPServer(string ipAddress, int port)
	: listenerIPAddress(ipAddress), listenerPort(port) {
}

TCPServer::~TCPServer() {
	cleanupWinsock();			//Cleanup Winsock when the server shuts down. 
}


//Function to check whether we were able to initialize Winsock & start the server. 
bool TCPServer::initWinsock() {

	WSADATA data;
	WORD ver = MAKEWORD(2, 2);

	int wsInit = WSAStartup(ver, &data);

	if (wsInit != 0) {
		cout << "Error: can't initialize Winsock." << std::endl;
		return false;
	}

	return true;

}


//Function that creates a listening socket of the server. 
SOCKET TCPServer::createSocket() {

	SOCKET listeningSocket = socket(AF_INET, SOCK_STREAM, 0);	//AF_INET = IPv4. 

	if (listeningSocket != INVALID_SOCKET) {

		sockaddr_in hint;		//Structure used to bind IP address & port to specific socket. 
		hint.sin_family = AF_INET;		//Tell hint that we are IPv4 addresses. 
		hint.sin_port = htons(listenerPort);	//Tell hint what port we are using. 
		inet_pton(AF_INET, listenerIPAddress.c_str(), &hint.sin_addr); 	//Converts IP string to bytes & pass it to our hint. hint.sin_addr is the buffer. 

		int bindCheck = bind(listeningSocket, (sockaddr*)&hint, sizeof(hint));	//Bind listeningSocket to the hint structure. We're telling it what IP address family & port to use. 

		if (bindCheck != SOCKET_ERROR) {			//If bind OK:

			int listenCheck = listen(listeningSocket, SOMAXCONN);	//Tell the socket is for listening. 
			if (listenCheck == SOCKET_ERROR)
				return -1;
		}

		else
			return -1;

		return listeningSocket;

	}

}

double** TCPServer::callRawUV(bool entrance)
{
	// The DoubleArray class represents arrays of double precision numbers. 
	// It encapsulates a pointer to a C array and the size of the array in a single object as follows:
	DoubleArray wavelengthArray; // DoubleArray : ChartDirector 7.0 (C++ Edition)
	DoubleArray spectrumArray;
	DoubleArray sepWavelengthArray;
	DoubleArray sepSpectrumArray;
	DoubleArray referenceArray;
	DoubleArray darkArray;
	Wrapper wrapper;
	VIS_NIR_LightSource vis_nir_lightsource;
	UV_VIS_LightSource uv_vis_lightsource;
	CoreAbsorbance coreabsorbance;
	CoreTransmission coretransimission;
	RamanShift ramanShift;

	// File I/O (upload reference spectrum, dark spectrum)
	ifstream is; // 읽기 변수 선언 
	double read_reference_pixel_data[4096]{}; // Original text : reference pixel spectrum 
	double read_dark_pixel_data[4096]{}; // Original text : reference dark pixel spectrum
	double mod_reference_pixel_data[2048]{}; // Original text : final dark pixel spectrum
	double mod_dark_pixel_data[2048]{}; // Original text : final dark pixel spectrum
	double reference_empty_data[1644]{}; // Original text : final dark pixel spectrum
	double dark_empty_data[1644]{}; // Original text : final dark pixel spectrum
	double sep_wavelength_data[1644]{}; // Original text : sep_wavelength_data
	double sep_spectrum_data[1644]{}; // Original text : sep_spectrum_data
	double* sep_spectrum;
	double* sep_wavelength;

	// Set parameter about UV variable
	int integrationTime; // units: microseconds
	int spectrometerIndex = 0; // 0-n; selects which spectrometer // you are talking 
	int numberOfSpectrometersAttached;

	// read reference spectrum
	/* 
	if (is.good()) {
		is.open("Reference_Spectrum_DIwater.txt"); // open text file
		if (is.is_open()) {
			for (int i = 0; i < 4096; i++) { // i : wavelength or spectrum's data size
				is >> read_reference_pixel_data[i];
			};
		}
		else {
			cout << "Reference_Spectrum_DIwater text file is not found" << endl;
		};
		is.close();
	}
	

	// make reference spectrum
	for (int i = 322; i < 1966; i++) {
		mod_reference_pixel_data[i - 322] = read_reference_pixel_data[(2 * i) + 1];
	}
	reference_spectrum = mod_reference_pixel_data;
	referenceArray.setValues(reference_spectrum, 1644);

	// read dark spectrum
	if (is.good()) {
		is.open("Dark_Spectrum_DIwater.txt"); // 텍스트 파일 오픈 ( array_data.txt라는 파일이 같은 폴더 내에 존재해야 합니다. )
		if (is.is_open()) {
			for (int i = 0; i < 4096; i++) { // i : wavelength or spectrum's data size
				is >> read_dark_pixel_data[i];
			};
		}
		else {
			cout << "Dark_Spectrum_DIwater text file is not found" << endl;
		};
		is.close();
	}

	// make darkArray
	for (int i = 322; i < 1966; i++) {
		mod_dark_pixel_data[i - 322] = read_dark_pixel_data[(2 * i) + 1];
	}
	dark_spectrum = mod_dark_pixel_data;
	darkArray.setValues(dark_spectrum, 1644);
	*/

	for (int i = 0; i < 1644; i++) {					// reference empty
		reference_empty_data[i] = 0;
	};
	referenceArray.setValues(reference_empty_data, 1644);
	for (int i = 0; i < 1644; i++) {					// dark empty 
		dark_empty_data[i] = 0;
	};
	darkArray.setValues(dark_empty_data, 1644);

	numberOfSpectrometersAttached = wrapper.openAllSpectrometers();
	cout << "Number of spectrometers found: " << numberOfSpectrometersAttached << endl;

	// set configuration's parameter
	spectrometerIndex = 0;
	// set integrationTime
	integrationTime = 14000; //  microseconds
	wrapper.setIntegrationTime(spectrometerIndex, integrationTime);
	// Set BoxcarWidth
	wrapper.setBoxcarWidth(spectrometerIndex, 10);
	// Set ScansToAverage
	wrapper.setScansToAverage(spectrometerIndex, 10);
	// set CorrectForDetectorNonlinearity
	wrapper.setCorrectForDetectorNonlinearity(spectrometerIndex, true);
	// set setCorrectForElectricalDark
	wrapper.setCorrectForElectricalDark(spectrometerIndex, true);
	// open spectrometer
	// set StrobeEnable
	wrapper.setAutoToggleStrobeLampEnable(spectrometerIndex, 1);

	// get spectrum array & wavelength array
	spectrumArray = wrapper.getSpectrum(spectrometerIndex);
	wavelengthArray = wrapper.getWavelengths(spectrometerIndex);			    // Retreives the wavelengths of the first spectrometer 
	// get spectrum value & wavelength value using getDoubleValues
	double* wavelengths = wavelengthArray.getDoubleValues();	// Sets a pointer to the values of the wavelength array 
	double* realSpectrum = spectrumArray.getDoubleValues();			// Sets a pointer to the values of the Spectrum array

	// seperate wavelength
	for (int i = 322; i < 1966; i++) {
		sep_wavelength_data[i - 322] = wavelengths[i];
	}
	sep_wavelength = sep_wavelength_data;
	sepWavelengthArray.setValues(sep_wavelength, 1644);
	// seperate spectrum
	for (int i = 322; i < 1966; i++) {
		sep_spectrum_data[i - 322] = realSpectrum[i];
	}
	sep_spectrum = sep_spectrum_data;
	sepSpectrumArray.setValues(sep_spectrum, 1644);


	// make result array using coreabsorbance.processSpectrum
	// DoubleArray ResultArray = coreabsorbance.processSpectrum(darkArray, referenceArray, sepSpectrumArray);
	// double* final_result = ResultArray.getDoubleValues();

	// Return Value
	double** value = new double* [2];
	value[0] = new double[1644];
	value[1] = new double[1644];

	for (int i = 0; i < 1644; i++) {					// Loop to print the spectral data to the screen
		// cout << "Wavelength: %1.2f      Spectrum: %f \n", wavelengths[i], realSpectrum[i];
		value[0][i] = sep_wavelength[i];
		value[1][i] = sep_spectrum[i];
	};

	return value;
}

double* TCPServer::callTargetUV(double** rawData)
{
	DoubleArray newWavelengthArray;
	DoubleArray neWResultArray;
	int spectrometerIndex = 0;
	double* newWavelength = rawData[0];
	double* newSpectrum = rawData[1];
	double* result = new double[2];
	
	// seperate wavelength
	newWavelengthArray.setValues(newWavelength, 1644);
	// seperate spectrum
	neWResultArray.setValues(newSpectrum, 1644);

	vector<double> temp_vector;
	for (int i = 0; i < 1644; i++) {
		// cout << "final_result data " << sep_wavelength[i] << ": " << final_result[i] << endl;
		temp_vector.push_back(newSpectrum[i]);
	}
	int max_index = max_element(newSpectrum, newSpectrum + 1644) - newSpectrum;
	result[0] = newWavelength[max_index]; // "Max Absorbance"

	SpectrumPeak* pSpectrumPeak = new SpectrumPeak(spectrometerIndex, newWavelengthArray, neWResultArray);
	//result[1] = pSpectrumPeak->getCenterWavelength();
	// result[2] = pSpectrumPeak->getCentroid();
	result[1] = pSpectrumPeak->getWavelengthFullWidthAtHalfMaximum();
	// result[3] = pSpectrumPeak->getIntegral();

	return result;
}

string TCPServer::date_time(tm* local_time) {
	string year = to_string(1900 + local_time->tm_year);
	string month = "";
	string day = "";
	string hour = "";
	string minute = "";
	string second = "";

	if ((1 + local_time->tm_mon) < 10)
		month = "0" + to_string(1 + local_time->tm_mon);
	else
		month = to_string(1 + local_time->tm_mon);
	
	if (local_time->tm_mday < 10)
		day = "0" + to_string(local_time->tm_mday);
	else
		day = to_string(local_time->tm_mday);

	if (local_time->tm_hour < 10)
		hour = "0" + to_string(local_time->tm_hour);
	else
		hour = to_string(local_time->tm_hour);

	if (local_time->tm_min < 10)
		minute = "0" + to_string(local_time->tm_min);
	else
		minute = to_string(local_time->tm_min);

	if (local_time->tm_sec < 10)
		second = "0" + to_string(local_time->tm_sec);
	else
		second = to_string(local_time->tm_sec);
	
	return year + month + day + "_" + hour + minute + second;
}

//Function doing the main work of the server -> evaluates sockets & either accepts connections or receives data. 
void TCPServer::run() {

	char buf[MAX_BUFFER_SIZE];		//Create the buffer to receive the data from the clients. 
	SOCKET listeningSocket = createSocket();		//Create the listening socket for the server. 
	cout << "UV server connection is created!" << endl;

	while (true) {

		if (listeningSocket == INVALID_SOCKET) {
			cout << listeningSocket << endl;
			cout << INVALID_SOCKET << endl;
			break;
		}

		fd_set master;				//File descriptor storing all the sockets.
		FD_ZERO(&master);			//Empty file file descriptor. 

		FD_SET(listeningSocket, &master);		//Add listening socket to file descriptor. 

		while (true) {

			fd_set copy = master;	//Create new file descriptor bc the file descriptor gets destroyed every time. 
			int socketCount = select(0, &copy, nullptr, nullptr, nullptr);				//Select() determines status of sockets & returns the sockets doing "work".
			for (int i = 0; i < socketCount; i++) {				//Server can only accept connection & receive msg from client. 

				SOCKET sock = copy.fd_array[i];					//Loop through all the sockets in the file descriptor, identified as "active". 

				if (sock == listeningSocket) {				//Case 1: accept new connection.

					SOCKET client = accept(listeningSocket, nullptr, nullptr);		//Accept incoming connection & identify it as a new client. 
					FD_SET(client, &master);		//Add new connection to list of sockets.  

					string welcomeMsg = "Connection accepted.\n";			//Notify client that he entered the chat. 
					cout << "Listening requests" << endl;			//Log connection on server side. 
				}
				else {										//Case 2: receive a msg.	
					ZeroMemory(buf, MAX_BUFFER_SIZE);		//Clear the buffer before receiving data. 
					int bytesReceived = recv(sock, buf, MAX_BUFFER_SIZE, 0);	//Receive data into buf & put it into bytesReceived. 
					if (bytesReceived <= 0) {	//No msg = drop client. 
						closesocket(sock);
						FD_CLR(sock, &master);	//Remove connection from file director.
					}
					else {						//Send msg to other clients & not listening socket.
						for (int i = 0; i < master.fd_count; i++) {			//Loop through the sockets. 
							SOCKET outSock = master.fd_array[i];
							if (outSock != listeningSocket) {
								if (outSock == sock) {		//If the current socket is the one that sent the message:
									if (bytesReceived > 0) {
										string message = string(buf, 0, bytesReceived); //Ag,01
										vector<string> command_info; // abs, Ag or hello, status
										stringstream splitter(message);
										while (splitter.good()) {
											string sub_str;
											getline(splitter, sub_str, ',');
											command_info.push_back(sub_str);
										};
										if (command_info[0] == "Abs")
										{
											int entrance = true;
											double** uv_analysis_raw_data = this->callRawUV(entrance);
											// double* uv_analysis_target_data = this->callTargetUV(uv_analysis_raw_data);

											// add element, cycle_number,
											vector<string> wavelength;
											vector<string> raw_spectrum;
											// vector<string> lambdamax;
											// vector<string> FWHM;
											// vector<string> CenterWavelength;
											// vector<string> Centroid;
											// vector<string> Integral;
											// vector<string> subNode_name;
											// vector<vector<string>> subNode_content;

											// make SubNode 
											// subNode_name.push_back("lambdamax");
											// subNode_name.push_back("FWHM");
											//subNode_name.push_back("CenterWavelength");
											//subNode_name.push_back("Centroid");
											//subNode_name.push_back("Integral");

											// insert content into vector temporaily
											for (int h = 0; h < 1644; h++)
											{
												wavelength.push_back(to_string(uv_analysis_raw_data[0][h]));
												raw_spectrum.push_back(to_string(uv_analysis_raw_data[1][h]));
											}
											//max_lambda.push_back(to_string(uv_analysis_target_data[0]));
											//max_FWHM.push_back(to_string(uv_analysis_target_data[1]));
											//CenterWavelength.push_back(to_string(uv_analysis_target_data[1]));
											//Centroid.push_back(to_string(uv_analysis_target_data[2]));
											//Integral.push_back(to_string(uv_analysis_target_data[3]));
											// insert content into SubNode
											//subNode_content.push_back(max_lambda);
											//subNode_content.push_back(max_FWHM);
											//subNode_content.push_back(CenterWavelength);
											//subNode_content.push_back(Centroid);
											//subNode_content.push_back(Integral);
											time_t ttime = time(0);
											tm* local_time = localtime(&ttime);
											string date_time = this->date_time(local_time);
											// command_info[0] : Metal Name, command_info[1] : Cycle Num
											// string json_filename = date_time + "_" + command_info[0] + "_" + command_info[1] + ".json";
											string json_filename = "C:/Data/" + date_time + "_" + command_info[0] + "_" + command_info[1] + ".json";
											JSONWriter json(json_filename);

											json.addNode("Wavelength", wavelength, "array");
											json.addNode("RawSpectrum", raw_spectrum, "array");
											//json.addNode("Property", subNode_name, "list");
											//json.addSubNode(subNode_content);
											json.close();

											cout << json_filename << endl;

											// execute json file (insert json into DB)
											// string command_python = string("python insert_json.py --json_file ") + json_filename.c_str() + " --element " + command_info[0] + " --cycle_number " + command_info[1];
											// cout << command_python << endl;
											// const char* c = command_python.c_str();
											// system(c);
											string msgSent = "Succeed to Analysis !";
											send(outSock, json_filename.c_str(), json_filename.size(), 0);

											cout << "Succeed to Analysis !" << endl;
										}
										else if(command_info[0] == "hello")
										{
											string msgSent = "Hello World!! Succeed to connection to main computer!";
											send(outSock, msgSent.c_str(), msgSent.size(), 0);
										}
										else if (command_info[0]=="Reference")
										{
											int entrance = true;
											double** uv_analysis_raw_data = this->callRawUV(entrance);
											double* uv_analysis_target_data = this->callTargetUV(uv_analysis_raw_data);

											// add element, cycle_number,
											vector<string> wavelength;
											vector<string> raw_spectrum;

											// insert content into vector temporaily
											for (int h = 0; h < 1644; h++)
											{
												wavelength.push_back(to_string(uv_analysis_raw_data[0][h]));
												raw_spectrum.push_back(to_string(uv_analysis_raw_data[1][h]));
											}
											time_t ttime = time(0);
											tm* local_time = localtime(&ttime);
											string date_time = this->date_time(local_time);
											string json_filename = "C:/Data/" + date_time + "_" + command_info[0] + "_" + command_info[1] + ".json";
											JSONWriter json(json_filename);

											json.addNode("Wavelength", wavelength, "array");
											json.addNode("RawSpectrum", raw_spectrum, "array");
											json.close();

											cout << json_filename << endl;

											string msgSent = "Succeed to Analysis !";
											send(outSock, json_filename.c_str(), json_filename.size(), 0);

											cout << "Succeed to Analysis !" << endl;
										}
										else if (command_info[0] == "Dark")
										{
											int entrance = false;
											double** uv_analysis_raw_data = this->callRawUV(entrance);
											double* uv_analysis_target_data = this->callTargetUV(uv_analysis_raw_data);

											// add element, cycle_number,
											vector<string> wavelength;
											vector<string> raw_spectrum;

											// insert content into vector temporaily
											for (int h = 0; h < 1644; h++)
											{
												wavelength.push_back(to_string(uv_analysis_raw_data[0][h]));
												raw_spectrum.push_back(to_string(uv_analysis_raw_data[1][h]));
											}
											time_t ttime = time(0);
											tm* local_time = localtime(&ttime);
											string date_time = this->date_time(local_time);
											string json_filename = "C:/Data/" + date_time + "_" + command_info[0] + "_" + command_info[1] + ".json";
											JSONWriter json(json_filename);

											json.addNode("Wavelength", wavelength, "array");
											json.addNode("RawSpectrum", raw_spectrum, "array");
											json.close();

											cout << json_filename << endl;

											string msgSent = "Succeed to Analysis !";
											send(outSock, json_filename.c_str(), json_filename.size(), 0);

											cout << "Succeed to Analysis !" << endl;
										}
									}
								}
							}
						}
					}
				}
			}
		}
	}
}


//Function to send the message to a specific client. 
void TCPServer::sendMsg(int clientSocket, std::string msg) {

	send(clientSocket, msg.c_str(), msg.size() + 1, 0);

}


void TCPServer::cleanupWinsock() {

	WSACleanup();

}
