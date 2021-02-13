#include <TFT_eSPI.h> // Graphics and font library for ILI9341 driver chip
#include <SPI.h>
#define FF1 &FreeMono9pt7b
#define BUF_LEN 64

TFT_eSPI tft = TFT_eSPI();  // Invoke library
unsigned int idx = 0;
char buffer[BUF_LEN];

unsigned int colors [] = {
  TFT_BLACK      , // 0
  TFT_NAVY       ,
  TFT_DARKGREEN  ,
  TFT_DARKCYAN   ,
  TFT_MAROON     ,
  TFT_PURPLE     , // 5
  TFT_OLIVE      ,
  TFT_LIGHTGREY  ,
  TFT_DARKGREY   ,
  TFT_BLUE       ,
  TFT_GREEN      , // 10
  TFT_CYAN       ,
  TFT_RED        ,
  TFT_MAGENTA    ,
  TFT_YELLOW     ,
  TFT_WHITE      , // 15
  TFT_ORANGE     ,
  TFT_GREENYELLOW,
  TFT_PINK
};

void setup() {

  tft.init();
  tft.setRotation(1);

  SerialUSB.begin(115200, SERIAL_8N1);

  tft.fillScreen(TFT_BLACK);
  // Set the font colour to be white with a black background, set text size multiplier to 1
  tft.setTextColor(TFT_WHITE, TFT_BLACK);

}


void loop() {

  int c = -1;

  if (SerialUSB.available()) {

    c = SerialUSB.read();

    if (c != -1) {

      if (idx < 24) {
        buffer[idx++] = (char)c;
      }

      if (c == 0) {

        char x = buffer[0];
        char line = buffer[1];
        char fsize = buffer[2];
        char color = buffer[3];
        
        // Set the font colour to be white with a black background, set text size multiplier to 1
        if (color == 0x7F) {
          tft.fillScreen(TFT_BLACK);
          tft.setCursor(x, line, 1);  
        } else {
          tft.setCursor(x, line, 1);  
          if (color < sizeof(colors)) {
            tft.setTextColor(colors[color], TFT_BLACK);
          } else {
            tft.setTextColor(TFT_WHITE, TFT_BLACK);
          }
          tft.setTextSize(fsize);
          // We can now plot text on screen using the "print" class
          char *ptr = &buffer[4];
          tft.println(F(ptr));
          
        }

        idx = 0;
      }
    }

  }

}
