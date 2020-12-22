# Home Assistant Ampio Custom Integration

[![GH-release](https://img.shields.io/github/v/release/kstaniek/ampio-hacc.svg?style=flat-square)](https://github.com/kstaniek/ampio-hacc/releases)
[![GH-downloads](https://img.shields.io/github/downloads/kstaniek/ampio-hacc/total?style=flat-square)](https://github.com/kstaniek/ampio-hacc/releases)
[![GH-last-commit](https://img.shields.io/github/last-commit/kstaniek/ampio-hacc.svg?style=flat-square)](https://github.com/kstaniek/ampio-hacc/commits/master)
[![GH-code-size](https://img.shields.io/github/languages/code-size/kstaniek/ampio-hacc.svg?color=red&style=flat-square)](https://github.com/kstaniek/ampio-hacc)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=flat-square)](https://github.com/hacs)


[![Ampio](https://ampio.pl/wp-content/themes/1140FluidStarkers/images/ampio_dark.png)](https://ampio.pl)

This is the custom integration of Ampio Smart Home System with  Home Assistant.

It uses MQTT connecting directly to the MQTT broker running on Ampio Server.

Currently there are following modules supported:
- MSERV-3s - flags
- MCON - Satel only
- MSENS - Both types
- MROL-4s
- MPR-8s
- MOC-4
- MRT-16s
- MLED-1
- MDIM-8s
- MRGBu-1
- MDOT-2
- MDOT-4
- MDOT-9
- MDOT-15LCD

The integation works with Ampio MQTT Bridge version: 3.41.2

## Installtion
Copy the ampio folder and all of its contents into your Home Assistant's custom_components folder. This is often located inside of your /config folder. If you are running Hass.io, use SAMBA to copy the folder over. If you are running Home Assistant Supervised, the custom_components folder might be located at /usr/share/hassio/homeassistant. It is possible that your custom_components folder does not exist. If that is the case, create the folder in the proper location, and then copy the localtuya folder and all of its contents inside the newly created custom_components folder.

Alternatively, you can install Ampio integration through HACS by adding this repository.

## Configuration

Start by going to Configuration - Integration and pressing the "+" button to create a new Integration, then select Ampio in the drop-down menu.

![config](https://github.com/kstaniek/ampio-hacc/blob/master/static/config1.png)

Provide the Ampio server IP address and leave default port number.
The username should be admin and with the admin pasword configured for Ampio Smart Home Application.
Click `Submit` button.

![config](https://github.com/kstaniek/ampio-hacc/blob/master/static/config2.png)

Click `Finish`

Once you finish the configuration you should see the Ampio integration on the list of installe integration with the number of discovered items.

![config](https://github.com/kstaniek/ampio-hacc/blob/master/static/config3.png)

The configuratio is done.

## Thanks to

Okek from Ampio for help, patience and effort to build the stable MQTT Broker for Ampio Smart Home System.  
