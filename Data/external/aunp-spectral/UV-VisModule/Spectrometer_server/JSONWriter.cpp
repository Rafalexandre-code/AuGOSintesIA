#define WIN32

#include <iostream>
#include <fstream>
#include <windows.data.json.h>
#include "JSONWriter.h"


using namespace std;

JSONWriter::JSONWriter(string filename) {
	this->json_filename = filename;
	this->jsonwrite = ofstream(this->json_filename);
}

void JSONWriter::addNode(string node_name, vector<string> value, string node_type) {
	this->json_node.push_back(node_name);
	if (node_type == "array") {
		this->json_node_type.push_back(node_type);
		this->json_nodeContent.push_back(value);
		vector<vector<string>> temp;
		vector<string> tempvalue;
		tempvalue.push_back("");
		temp.push_back(tempvalue);
		this->json_subNodeContent.push_back(temp);
	} else if (node_type == "list") {
		this->json_node_type.push_back(node_type);
		this->json_nodeContent.push_back(value);
	}
	
	this->num_of_node++;
}


void JSONWriter::addSubNode(vector<vector<string>> value) {
	this->json_subNodeContent.push_back(value);
}


void JSONWriter::close() {
	this->jsonwrite << "{" << endl;
	this->jsonwrite << "\t\"Name\": \"" << this->json_filename << "\"," << endl;
	for (int i = 0; i < this->num_of_node; i++) {
		if (this->json_node_type.at(i) == "array") {
			this->jsonwrite << "\t\"" << this->json_node.at(i) << "\": \n\t[\n\t\t";
			for (int j = 0; j < this->json_nodeContent.at(i).size(); j++) {
				if (j == this->json_nodeContent.at(i).size()-1)
					this->jsonwrite << this->json_nodeContent.at(i).at(j) << "\n\t]";
				else
					this->jsonwrite << this->json_nodeContent.at(i).at(j) << ", ";
			}

			if (i != this->num_of_node - 1)
				this->jsonwrite << "," << endl;
		}
		else if (this->json_node_type.at(i) == "list") {
			this->jsonwrite << "\t\"" << this->json_node.at(i) << "\": \n\t{\n";
			for (int j = 0; j < this->json_nodeContent.at(i).size(); j++) {
				this->jsonwrite << "\t\t\"" << this->json_nodeContent.at(i).at(j) << "\": " << endl;
				this->jsonwrite << "\t\t[\n\t\t\t";
				for (int k = 0; k < this->json_subNodeContent.at(i).at(j).size(); k++) {
					if (k == this->json_subNodeContent.at(i).at(j).size()-1)
						this->jsonwrite << this->json_subNodeContent.at(i).at(j).at(k).c_str() << "\n" ;
					else
						this->jsonwrite << this->json_subNodeContent.at(i).at(j).at(k).c_str() << ", ";
				}
				if (j == this->json_nodeContent.at(i).size()-1)
					this->jsonwrite << "\t\t]\n";
				else
					this->jsonwrite << "\t\t],\n";
			}
			this->jsonwrite << "\t}";
		}
	}
	this->jsonwrite << "\n}";
	this->jsonwrite.close();
}