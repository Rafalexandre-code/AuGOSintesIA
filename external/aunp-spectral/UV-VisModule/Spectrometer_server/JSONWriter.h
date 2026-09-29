#pragma once

#include <string>
#include <vector>
#include <fstream>


using namespace std;

class JSONWriter {
public:
	JSONWriter(string filename);
	void addNode(string node_name, vector<string> value, string node_type);
	void addSubNode(vector<vector<string>> value);
	void close();
	
private:
	string json_filename;
	int num_of_node;
	ofstream jsonwrite;
	vector<string> json_node;
	vector<string> json_node_type;
	vector<int> json_numOfSubNode;
	vector<vector<string>> json_nodeContent;
	vector<vector<vector<string>>> json_subNodeContent;
};