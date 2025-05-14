#Troubleshooting
Here you will find help with common problems you might encounter when installing or using Album.

##Installation

###Windows
####Admin rights
On some Windows systems, especially virtual machines, the installer will trigger a request
for admin rights. This is because the installer of Micromamba needs to edit the powershell profile. 
The installer will only edit the profile of the current user and not the system profile. 
The installer will not install anything on your system without your permission. If you deny the request for
admin rights the installer will install album in a GUI only mode. This means that you can only use Album in the graphical
user interface and not in the commandline/powershell since they cannot be initialised without admin rights.

#### Windows blocks installer
If you face the problem, that windows is blocking the execution of the album installer please follow these steps:
1. Click on show more:
.. image:: _static/windows_block_1.png
    :width: 600
2. Click on run anyway:
.. image:: _static/windows_block_2.png
    :width: 600

###MacOS
####MacOS blocks installer
When you try to execute the installer on MacOS you might see a windows like this:
.. image:: _static/macos_block_1.png
    :width: 600
This means that macOS has blocked the execution of the installer. 
If you face that problem, please follow these steps:
1. Open your system preferences
2. Click on security and privacy:
.. image:: _static/macos_block_2.png
    :width: 600
3. Click on open anyway:
.. image:: _static/macos_block_3.png
    :width: 600
4. Click on open:
.. image:: _static/macos_block_4.png
    :width: 600



