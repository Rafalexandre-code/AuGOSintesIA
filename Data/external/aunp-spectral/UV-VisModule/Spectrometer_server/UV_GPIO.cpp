#pragma warning(disable : 4996)

#define WIN32

// Basic Library
#include <iostream>
#include <fstream>
#include <typeinfo>
#include <algorithm>
#include <vector>
// OmniDrivier Library
#include "Wrapper.h"
// Spam Library
#include "AdvancedPeakFinding.h"
#include "CoreAbsorbance.h"
#include "SpectralMath.h"
#include "SpectrumPeak.h"

using namespace std;
/*
int main(void) {

	// The DoubleArray class represents arrays of double precision numbers. 
	// It encapsulates a pointer to a C array and the size of the array in a single object as follows:
	DoubleArray wavelengthArray; // DoubleArray : ChartDirector 7.0 (C++ Edition)
	DoubleArray spectrumArray;
	DoubleArray sepWavelengthArray;
	DoubleArray sepSpectrumArray;
	DoubleArray referenceArray;
	DoubleArray darkArray;
	Wrapper wrapper;
	VIS_NIR_LightSource lightsource;
	CoreAbsorbance coreabsorbance;
	CoreTransmission coretransimission;
	RamanShift ramanShift;

	// File I/O (upload reference spectrum, dark spectrum)
	ifstream is; // 읽기 변수 선언 
	double read_reference_pixel_data[4096]{}; // Original text : reference pixel spectrum 
	double read_dark_pixel_data[4096]{}; // Original text : reference dark pixel spectrum
	double mod_reference_pixel_data[2048]{}; // Original text : final dark pixel spectrum
	double mod_dark_pixel_data[2048]{}; // Original text : final dark pixel spectrum
	double sep_wavelength_data[1644]{}; // Original text : sep_wavelength_data
	double sep_spectrum_data[1644]{}; // Original text : sep_spectrum_data
	double* sep_spectrum;
	double* sep_wavelength;
	double* reference_spectrum;
	double* dark_spectrum;

	// Set parameter about UV variable
	int integrationTime; // units: microseconds
	int spectrometerIndex = 0; // 0-n; selects which spectrometer // you are talking 
	int numberOfSpectrometersAttached;
	int	numberOfPixels;

	/*
	5 (0) - 326 (321) : (322)
	Content : (322 ~ 1965 : 1644)
	1971 (1966) - 2052 (2047) : (82)
	*/
	/*
	// read reference spectrum
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
		mod_dark_pixel_data[i - 322] = read_dark_pixel_data[(2 * i ) + 1];
	}
	dark_spectrum = mod_dark_pixel_data;
	darkArray.setValues(dark_spectrum, 1644);

	// open spectrometer
	numberOfSpectrometersAttached = wrapper.openAllSpectrometers();
	cout << "Number of spectrometers found: " << numberOfSpectrometersAttached << endl;

	 // set configuration's parameter
	spectrometerIndex = 0;
		// set integrationTime
	integrationTime = 20000; //  microseconds
	wrapper.setIntegrationTime(spectrometerIndex, integrationTime);
		// Set BoxcarWidth
	wrapper.setBoxcarWidth(spectrometerIndex, 10);
		// Set ScansToAverage
	wrapper.setScansToAverage(spectrometerIndex, 10);
		// set StrobeEnable
	wrapper.setStrobeEnable(spectrometerIndex, true);
		// set CorrectForDetectorNonlinearity
	wrapper.setCorrectForDetectorNonlinearity(spectrometerIndex, true);
		// set setCorrectForElectricalDark
	wrapper.setCorrectForElectricalDark(spectrometerIndex, true);
	for (int i = 0; i < 100; i++) {

		// get spectrum array & wavelength array
		spectrumArray = wrapper.getSpectrum(spectrometerIndex);
		wavelengthArray = wrapper.getWavelengths(spectrometerIndex);			    // Retreives the wavelengths of the first spectrometer 
	
		// get pixel number
		// int darkArrayOfPixels = darkArray.getLength();
		// int referenceArrayOfPixels = referenceArray.getLength();
		// cout << "darkArrayOfPixels : " << darkArrayOfPixels << endl;
		// cout << "referenceArrayOfPixels : " << darkArrayOfPixels << endl;

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

		// for (int i = 0; i < 1644; i++) {
			// cout << "sep_spectrum data " << sep_wavelength[i] << ": " << sep_spectrum[i] << endl;
			//cout << sep_spectrum[i] << endl;
		// }
		// for (int i = 0; i < 1644; i++) {
			// cout << "sep_wavelength data " << sep_wavelength[i] << ": " << sep_spectrum[i] << endl;
			//cout << sep_wavelength[i] << endl;
		// }

		// check reference spectrum & dark spectrum's type
		// cout << "final_dark_pixel_data type : " << typeid(final_dark_pixel_data).name() << endl;
		// cout << "final_reference_pixel_data type : " << typeid(final_reference_pixel_data).name() << endl;

		// make result array using coreabsorbance.processSpectrum
		DoubleArray ResultArray = coreabsorbance.processSpectrum(darkArray, referenceArray, sepSpectrumArray);
	
		// seperate pixel number
		// int sepSpectrumArrayOfPixels = sepSpectrumArray.getLength();
		// cout << "sepSpectrumArrayOfPixels : " << sepSpectrumArrayOfPixels << endl;
		double* final_result = ResultArray.getDoubleValues();
		vector<double> temp_vector;
		for (int i = 0; i < 1644; i++) {
			// cout << "final_result data " << sep_wavelength[i] << ": " << final_result[i] << endl;
			temp_vector.push_back(final_result[i]);
		}
		// int max_value = *max_element(final_result, final_result+1644);
		// cout << "max value : " << max_value << "\n";
		int max_index = max_element(final_result, final_result + 1644) - final_result;
		// cout << "max value index : " << sep_wavelength[max_index] << "\n";
		cout << sep_wavelength[max_index] << "\n";
	}
	//for (int i = 0; i < 1644; i++) {
		// cout << "final_result data " << sep_wavelength[i] << ": " << final_result[i] << endl;
	//	cout << final_result[i] << endl;
	//}

	// check reference spectrum & dark spectrum
	//for (int i = 0; i < 1644; i++) {
	// 	//cout << "reference_spectrum data " << sep_wavelength[i] << ": " << reference_spectrum[i] << endl;
	//	cout << reference_spectrum[i] << endl;
	//}
	//for (int i = 0; i < 1644; i++) {
	// 	//cout << "dark_spectrum data " << sep_wavelength[i] << ": " << dark_spectrum[i] << endl;
	// 	cout << dark_spectrum[i] << endl;
	//}
	// Now use the SPAM functions to identify the peaks

	/*
	SpectralMath* pSpectralMath = new SpectralMath();
	int peakIndex = 100;
	AdvancedPeakFinding advancedPeakFinding;
	advancedPeakFinding = pSpectralMath->createAdvancedPeakFindingObject();
	int startingIndex = 0;
	int minimumIndicesBetweenPeaks = 100;
	double baseline = 100.0;
	int indexOfPeak;
	do
	{
		indexOfPeak = advancedPeakFinding.getNextPeakIndex(yDoubleArray, startingIndex, minimumIndicesBetweenPeaks, baseline);
		if (indexOfPeak == 0)
			break;
		printf("index of peak = %d\n", indexOfPeak);
		startingIndex = indexOfPeak;
	} while (indexOfPeak > 0);

	printf("peak X value %f\n", spectrumPeak.getPeakXValue());
	delete pSpectralMath;

	SpectrumPeak* pSpectrumPeak = new SpectrumPeak(spectrometerIndex, sepWavelengthArray, ResultArray);
	// DoubleArray sample = pSpectrumPeak->getAllPeaks(wavelengthArray, ResultArray, 100, 0);
	// cout << "getAllPeaks : " <<  << endl;
	cout << "CenterWavelength : " << pSpectrumPeak->getCenterWavelength()+300.125 << endl;
	cout << "Centroid : " << pSpectrumPeak->getCentroid() + 300.125 << endl;
	cout << "wavelength FullWidthAtHalfMaximum : " <<pSpectrumPeak->getWavelengthFullWidthAtHalfMaximum() << endl;
	cout << "pixel FullWidthAtHalfMaximum : " << pSpectrumPeak->getPixelFullWidthAtHalfMaximum() << endl;
	cout << "Integral : " << pSpectrumPeak->getIntegral() << endl;
	cout << "PixelNumber : " << pSpectrumPeak->getPixelNumber() << endl;
	*/

	/*
	// Raman Spectrum

	// Return Value
	double** value = new double* [2];
	value[0] = new double[numberOfPixels];
	value[1] = new double[numberOfPixels];

	for (int i = 0; i < numberOfPixels; i++) {					// Loop to print the spectral data to the screen
		// cout << "Wavelength: %1.2f      Spectrum: %f \n", wavelengths[i], realSpectrum[i];
		value[0][i] = wavelengths[i];
		value[1][i] = final_result[i];
	};

	GPIO gpiocontroller = wrapper.getFeatureControllerGPIO(spectrometerIndex);
	
	// Set the mode: false is normal GPIO mode; 
	// true is "alternate function" mode
	gpiocontroller.setMuxBit(2, false);
	gpiocontroller.setMuxBit(3, false);
	gpiocontroller.setMuxBit(13, false);

	// Set the direction: true is output, false is input
	gpiocontroller.setDirectionBit(2, false);
	gpiocontroller.setDirectionBit(3, false);
	gpiocontroller.setDirectionBit(13, false);
	
	// Read all 10 GPIO bits into our buffer, even if some of them were 
	// set to output (we will simply ignore those bits)
	int data_1 = gpiocontroller.getValueBits().get(2);
	int data_2 = gpiocontroller.getValueBits().get(3);
	int data_3 = gpiocontroller.getValueBits().get(13);

	cout << "Data_1 : " << data_1 << endl;
	cout << "Data_2 : " << data_2 << endl;
	cout << "Data_3 : " << data_3 << endl;
	
	return 0;
}

*/