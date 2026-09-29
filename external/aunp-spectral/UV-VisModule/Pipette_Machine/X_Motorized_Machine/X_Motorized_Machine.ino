//Globals
#define stepPin 6
#define dirPin 7

String serialData;



void setup() {
  Serial.begin(9600);
  // Declare pins as output:
  pinMode(stepPin, OUTPUT);
  pinMode(dirPin, OUTPUT);
  // Set the spinning direction CW/CCW:
  digitalWrite(dirPin, HIGH);

}

// 30
void loop() {
  // These four lines result in 1 step:
  if(Serial.available() > 0) {
    serialData = Serial.readString();
    int value = serialData.toInt();
    if(value > 0) {
      forward(value*200);
    }
    else {
      reverse(abs(value*200));
    }
  }
}

void forward(int stepsPerRevolution) {
  // Set the spinning direction clockwise:
  digitalWrite(dirPin, HIGH);
  // Spin the stepper motor 5 revolutions fast:
  for (int i = 0; i < stepsPerRevolution; i++) {
    // These four lines result in 1 step:
    digitalWrite(stepPin, HIGH);
    delayMicroseconds(500);
    digitalWrite(stepPin, LOW);
    delayMicroseconds(500);
  }

}


void reverse(int stepsPerRevolution) {
  // Set the spinning direction clockwise:
  digitalWrite(dirPin, LOW);
  // Spin the stepper motor 5 revolutions fast:
  for (int i = 0; i < stepsPerRevolution; i++) {
    // These four lines result in 1 step:
    digitalWrite(stepPin, HIGH);
    delayMicroseconds(500);
    digitalWrite(stepPin, LOW);
    delayMicroseconds(500);
  }
}
