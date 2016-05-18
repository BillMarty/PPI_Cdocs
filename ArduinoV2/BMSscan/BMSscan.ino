// BMSscanRevB
// 4-13-2016  - Changed 30% SOC to be 1-30%, 0% SOC does not trip output
//            Sketch = 3140 bytes
//            Globals = 333 bytes
//            using Arduino 1.6.8 on Win7
//  
#define LED  13
#define cnts 100
#define CAP30 3   // I/O pin for 30% SOC output
#define CAP80 2   // I/O pin for 80% SOC output
#define CAPHI 65  // Turn off SOC
#define CAPLOW 30 // Turn on SOC

// ***** To Do:   SOC=0 is special case at power up, ignore for 30% SOC signal *****
char linebuf[135];
//char linebuf[]="001,S,122,002,00,C,043,022,288349,-0200,80000000,002,1511120015700,887 ,842 ,004543,006017,003735,003755,025,            ,CA74";
//char linebuf[]="001,S,122,732,00,R,043,022,279114,00004,80000000,002,1511120015700,887 ,842 ,004543,006017,003620,003629,026,            ,CC79";
unsigned int flech1, fletch2;  // used to calculate Fletcher checksum of received BMS messageds

void blink(int pin,int cnt)
{
  pinMode(pin,OUTPUT);
  digitalWrite(pin,HIGH);
  delay(cnts);
  
  digitalWrite(pin,LOW);
  delay(cnts);
}

// Read a line from the serial port and place it in a buffer
// return the number of chars read, zero if timeout occured

int readLine(char* buf, int maxcnt)
{
  //return(sizeof(linebuf)); //--debug
  #define timeout 15000
  int nchars =0;
  unsigned long tmax;
  
  tmax = millis() + timeout;  // remember when we started scanning for a line
  while (tmax < millis())  // wait for wrap around? (once every 50 days)
    ;
    
  while ((nchars < maxcnt) && (millis()< tmax))
  {  
    if (Serial.available()>0)  //read a buffer, watching for NewLine
    {
      buf[nchars] = Serial.read();
      if (buf[nchars] == '\n')
      {
        linebuf[nchars]=0;  //terminate the string
        break;
      }
      nchars++;
    }
  }
  return nchars;  
}

void setup() {
  // put your setup code here, to run once:
  Serial.begin(9600);
  while (!Serial) {
    ; // wait for serial port to connect. Needed for native USB port only
  }
  blink(LED,cnts);
  blink(LED,cnts);
  Serial.print("BMSscanRev3065");
}

void loop() {
  // put your main code here, to run repeatedly:
  int chars = readLine(linebuf,sizeof(linebuf));
  //Serial.print("Fletcher-16 ");
  //Serial.println(fletcherCheck(linebuf,chars),HEX);
  
  if ((chars > 0) && (chars < sizeof(linebuf)))
  {
    if (linebuf[4]=='S')
    {
      // get State of Charge
      int soc = linebuf[19]-'0';
      soc *= 10;
      soc += linebuf[20]-'0';
      soc *= 10;
      soc += linebuf[21]-'0';
      analogWrite(5,(soc*256)/100);

      // update digital Open Drain outputs
      pinMode(CAP80,OUTPUT);
      if( soc >= CAPHI)
      {
 
        digitalWrite(CAP80,HIGH);
      }
      else
        digitalWrite(CAP80,LOW);

      pinMode(CAP30,OUTPUT);
      if ((soc <= CAPLOW) && (soc > 0))
        digitalWrite(CAP30,HIGH);
      else
        digitalWrite(CAP30,LOW);
      
      // get +/- Battery Current
      int cur = linebuf[35]-'0';
      cur *= 10;
      cur += linebuf[36]-'0';
      cur *= 10;
      cur += linebuf[37]-'0';
      cur *= 10;
      cur += linebuf[38]-'0';
      //if (linebuf[34]=='-') cur *= -1;
      analogWrite(6,cur);
      
      blink(LED,cnts);
    }
  }
  //blink(LED,cnts);
}

unsigned fletcherCheck(char* buf, int nchars)
{
  unsigned sum1=0, sum2=0;
  for (int i=0;i<nchars;i++)
  {
    sum1 = (sum1 + buf[i]);
    if (sum1 >= 255) sum1 -= 255;
    sum2 = (sum1 + sum2);
    if (sum2 >= 255) sum2 -= 255;
    Serial.print(buf[i],HEX);
    Serial.print("  ");
    Serial.print(sum1,HEX);
    Serial.print("  ");
    Serial.println(sum2,HEX);
  }
  return sum1 | (sum2<<8);
}


