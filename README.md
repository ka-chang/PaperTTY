# PaperTTY

This module is a fork of [joukos/PaperTTY](https://github.com/joukos/PaperTTY), 
modified to be specifically designed for devices with the IT8951 controller.

The main changes are:

1. Parsing of character attributes, including background and foreground color,
 to take advantage of the 16 levels of grayscale provided by the IT8951
2. Use of different waveform modes (fast or slower update, some or little ghosting) 
 to optimally display characters in various situations. For example, as characters are
 typed they are displayed as fast as possible using black-and-white only updates, 
 but e.g. grayscale updates of highlighting in Emacs are displayed with the slower 
 grayscale mode.
3. Ability to have another process take over the display! (see below)
4. Removal of VNC support. I think that would have to be another package, this 
 one is big enough as is.
 
## Setting up

First install the IT8951 driver [here](https://github.com/GregDMeyer/IT8951).

Next clone the repository and install the required packages: 
`pip3 install -r requirements.txt`

Now you can test out PaperTTY. 
Enter the `bin` directory and edit `start.sh`
to contain the appropriate paths.
Finally, run `sudo start.sh` and watch the e-paper terminal (hopefully) come to life!

If you want to always run PaperTTY at startup, do the following:
 1. Modify the file `papertty.service` to contain the appropriate paths
 2. Run the following commands:
 
```
sudo cp papertty.service /etc/systemd/system
sudo systemctl daemon-reload
sudo systemctl enable papertty
```

Now PaperTTY is registered as a service, and you can try it out by running e.g.
`sudo systemctl start papertty`
and stop it with 
`sudo systemctl stop papertty`.

Next time you boot, it should start up!

__Note:__ If you want to be able to just plug in a keyboard to your Raspberry Pi 
and boot to a terminal you can type in, don't forget to set your Pi to boot into
console mode rather than graphical mode! PaperTTY will just show whatever tty1 is
doing (by default), so you need to make sure you're actually typing into tty1!

## Using the display from other processes

My goal with this project was not just to show the terminal on the e-paper display;
I wanted to be able to write scripts I could run from that terminal that would show
their *own* cool stuff on the display. The general issue with that is that PaperTTY
already has control of the display, so another process trying to write to it at the
same time would not work well. So, I set up PaperTTY to listen for other processes
that want to use the display, display their data while they are running, and then
show the terminal again when the other process is done with it. 

For an example of this, with PaperTTY running, go into the `tests/` directory
of this repository and run `python3 test_controller.py`. You should see various images
flash on the display, and then afterward the terminal should be displayed again.

I think one of the coolest things about this strategy is that you don't need to 
run these other scripts as root. Normally, to use the e-paper you need root so 
that you can write via SPI, etc. But since PaperTTY takes care of actually talking
to the display, you can just run as an unprivileged user and give the data to 
PaperTTY running as root!