# Remote Setup Script

This Python script performs a remote kubernetes worker setup on a server using SSH. It is designed to automate the installation and configuration of various components.

## Requirements

- Python 3.x
- `paramiko` library: Install it using `pip install paramiko`

## Usage

1. Clone the repository:

   ```bash
   git clone https://github.com/aberekerehu/python-script-to-install-k8s-controlPlane-and-pods.git
   cd kubernetes

1. Install the required Python library:
pip install paramiko

2. Open the install_worker.py and install_control_plane.py file and update the following variables with your remote server details:

host = 'your_remote_server_ip'
username = 'your_username'
password = 'your_password'

3. Run the script:
python remote_setup.py

