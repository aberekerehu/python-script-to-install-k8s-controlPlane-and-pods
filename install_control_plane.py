import paramiko
import subprocess
import sys

# Remote server details
host = 'your_remote_server_ip'
username = 'your_username'
password = 'your_password'

def run_remote_command(ssh, command):
    stdin, stdout, stderr = ssh.exec_command(command)
    exit_code = stdout.channel.recv_exit_status()
    if exit_code != 0:
        print(f"Error executing command remotely: {command}")
        print(f"Exit code: {exit_code}")
        sys.exit(1)

def check_install_package(ssh, package):
    check_command = f"dpkg-query -W -f='${{Status}}' {package} 2>/dev/null | grep -c 'ok installed'"
    stdin, stdout, stderr = ssh.exec_command(check_command)
    exit_code = stdout.channel.recv_exit_status()
    if exit_code != 0:
        print(f"Error checking package {package} status remotely.")
        sys.exit(1)
    else:
        is_installed = int(stdout.read().decode().strip())
        if is_installed == 0:
            print(f"{package} is not installed. Installing...")
            run_remote_command(ssh, f"sudo apt-get install -y {package}")

def main():
    # SSH connection
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=username, password=password)

    # Source: http://kubernetes.io/docs/getting-started-guides/kubeadm
    KUBE_VERSION = "1.23.6"

    # Check Ubuntu version
    run_remote_command(ssh, "source /etc/lsb-release")
    ubuntu_version_command = "lsb_release -r -s"
    ubuntu_version = subprocess.check_output(f"ssh {username}@{host} {ubuntu_version_command}", shell=True).decode().strip()
    if ubuntu_version != "20.04":
        print("=====WARNING ======")
        print("\nThis script only works on Ubuntu 20.04!")
        print(f"You're using: {subprocess.check_output(f'ssh {username}@{host} lsb_release -d -s', shell=True).decode().strip()}")
        print("Better ABORT with Ctrl+C. Or press any key to continue the install")
        input()

    # Setup terminal

    run_remote_command(["apt-get", "update"])
    run_remote_command(["wget", "-qO", "-", "https://download.opensuse.org/repositories/devel:/kubic:/libcontainers:/stable/xUbuntu_20.04/Release.key", "|", "sudo", "apt-key", "add", "-"])
    run_remote_command(["apt-get", "install", "-y", "bash-completion", "binutils"])
    run_remote_command(["echo", "'colorscheme ron'", ">>", "~/.vimrc"])
    run_remote_command(["echo", "'set tabstop=2'", ">>", "~/.vimrc"])
    run_remote_command(["echo", "'set shiftwidth=2'", ">>", "~/.vimrc"])
    run_remote_command(["echo", "'set expandtab'", ">>", "~/.vimrc"])
    run_remote_command(["echo", "'source <(kubectl completion bash)'", ">>", "~/.bashrc"])
    run_remote_command(["echo", "'alias k=kubectl'", ">>", "~/.bashrc"])
    run_remote_command(["echo", "'alias c=clear'", ">>", "~/.bashrc"])
    run_remote_command(["echo", "'complete -F __start_kubectl k'", ">>", "~/.bashrc"])
    run_remote_command(["sed", "-i", '1s/^/force_color_prompt=yes\n/', "~/.bashrc"])

    # Disable Linux swap and remove any existing swap partitions
    run_remote_command(["swapoff", "-a"])
    run_remote_command(["sed", "-i", '/\sswap\s/ s/^\(.*\)$/#\1/g', "/etc/fstab"])

    # Remove packages
    run_remote_command(["kubeadm", "reset", "-f", "||", "true"])
    run_remote_command(["crictl", "rm", "--force", "$(crictl ps -a -q)", "||", "true"])
    run_remote_command(["apt-mark", "unhold", "kubelet", "kubeadm", "kubectl", "kubernetes-cni", "||", "true"])
    run_remote_command(["apt-get", "remove", "-y", "docker.io", "containerd", "kubelet", "kubeadm", "kubectl", "kubernetes-cni", "||", "true"])
    run_remote_command(["apt-get", "autoremove", "-y"])
    run_remote_command(["systemctl", "daemon-reload"])

    # Install podman
    os_release = subprocess.check_output(["cat", "/etc/os-release"]).decode()
    run_remote_command(["echo", f'deb https://download.opensuse.org/repositories/devel:/kubic:/libcontainers:/testing/xUbuntu_{os_release}/ /" | sudo tee /etc/apt/sources.list.d/devel:kubic:libcontainers:testing.list'])
    run_remote_command(["curl", "-L", f"https://download.opensuse.org/repositories/devel:/kubic:/libcontainers:/testing/xUbuntu_{os_release}/Release.key", "|", "sudo", "apt-key", "add", "-"])
    run_remote_command(["apt-get", "update", "-qq"])
    run_remote_command(["apt-get", "-qq", "-y", "install", "podman", "cri-tools", "containers-common"])
    run_remote_command(["rm", "/etc/apt/sources.list.d/devel:kubic:libcontainers:testing.list"])
    run_remote_command(["cat", "<<EOF | sudo tee /etc/containers/registries.conf", "[registries.search]", 'registries = ["docker.io"]', "EOF"])

    # Install packages
    run_remote_command(["curl", "https://packages.cloud.google.com/apt/doc/apt-key.gpg", "|", "apt-key", "add", "-"])
    run_remote_command(["echo", 'deb http://apt.kubernetes.io/ kubernetes-xenial main', "|", "tee", "/etc/apt/sources.list.d/kubernetes.list"])
    run_remote_command(["apt-get", "update"])
    run_remote_command(["apt-get", "install", "-y", "docker.io", "containerd", f"kubelet={KUBE_VERSION}-00", f"kubeadm={KUBE_VERSION}-00", f"kubectl={KUBE_VERSION}-00", "kubernetes-cni"])
    run_remote_command(["apt-mark", "hold", "kubelet", "kubeadm", "kubectl", "kubernetes-cni"])

    # Containerd
    run_remote_command(["cat", "<<EOF | sudo tee /etc/modules-load.d/containerd.conf", "overlay", "br_netfilter", "EOF"])
    run_remote_command(["sudo", "modprobe", "overlay"])
    run_remote_command(["sudo", "modprobe", "br_netfilter"])
    run_remote_command(["cat", "<<EOF | sudo tee /etc/sysctl.d/99-kubernetes-cri.conf", "net.bridge.bridge-nf-call-iptables  = 1", "net.ipv4.ip_forward                 = 1", "net.bridge.bridge-nf-call-ip6tables = 1", "EOF"])
    run_remote_command(["sudo", "sysctl", "--system"])
    run_remote_command(["sudo", "mkdir", "-p", "/etc/containerd"])

    # Containerd config
    containerd_config_content = """
    disabled_plugins = []
    imports = []
    oom_score = 0
    plugin_dir = ""
    required_plugins = []
    root = "/var/lib/containerd"
    state = "/run/containerd"
    version = 2

    [plugins]

    [plugins."io.containerd.grpc.v1.cri".containerd.runtimes]
        [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc]
        base_runtime_spec = ""
        container_annotations = []
        pod_annotations = []
        privileged_without_host_devices = false
        runtime_engine = ""
        runtime_root = ""
        runtime_type = "io.containerd.runc.v2"

        [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc.options]
            BinaryName = ""
            CriuImagePath = ""
            CriuPath = ""
            CriuWorkPath = ""
            IoGid = 0
            IoUid = 0
            NoNewKeyring = false
            NoPivotRoot = false
            Root = ""
            ShimCgroup = ""
            SystemdCgroup = true
    """

    with open("/etc/containerd/config.toml", "w") as config_file:
        config_file.write(containerd_config_content)

    # crictl uses containerd as default
    crictl_config_content = """
    runtime-endpoint: unix:///run/containerd/containerd.sock
    """

    with open("/etc/crictl.yaml", "w") as crictl_config_file:
        crictl_config_file.write(crictl_config_content)

    # kubelet should use containerd
    kubelet_config_content = """
    KUBELET_EXTRA_ARGS="--container-runtime remote --container-runtime-endpoint unix:///run/containerd/containerd.sock"
    """

    with open("/etc/default/kubelet", "w") as kubelet_config_file:
        kubelet_config_file.write(kubelet_config_content)

    # Start services
    run_remote_command(["systemctl", "daemon-reload"])
    run_remote_command(["systemctl", "enable", "containerd"])
    run_remote_command(["systemctl", "restart", "containerd"])
    run_remote_command(["systemctl", "enable", "kubelet"])
    run_remote_command(["systemctl", "start", "kubelet"])

    # Init K8s
    run_remote_command(["rm", "/root/.kube/config", "||", "true"])
    run_remote_command(["kubeadm", "init", f"--kubernetes-version={KUBE_VERSION}", "--ignore-preflight-errors=NumCPU", "--skip-token-print", "--pod-network-cidr", "192.168.0.0/16"])

    run_remote_command(["mkdir", "-p", "~/.kube"])
    run_remote_command(["sudo", "cp", "-i", "/etc/kubernetes/admin.conf", "~/.kube/config"])

    # CNI
    run_remote_command(["kubectl", "apply", "-f", "https://raw.githubusercontent.com/killer-sh/cks-course-environment/master/cluster-setup/calico.yaml"])

    # etcdctl
    ETCDCTL_VERSION = "v3.5.1"
    ETCDCTL_VERSION_FULL = f"etcd-{ETCDCTL_VERSION}-linux-amd64"
    run_remote_command(["wget", f"https://github.com/etcd-io/etcd/releases/download/{ETCDCTL_VERSION}/{ETCDCTL_VERSION_FULL}.tar.gz"])
    run_remote_command(["tar", "xzf", f"{ETCDCTL_VERSION_FULL}.tar.gz"])
    run_remote_command(["mv", f"{ETCDCTL_VERSION_FULL}/etcdctl", "/usr/bin/"])
    run_remote_command(["rm", "-rf", ETCDCTL_VERSION_FULL, f"{ETCDCTL_VERSION_FULL}.tar.gz"])

    print("\n### COMMAND TO ADD A WORKER NODE ###")
    print(subprocess.check_output(["kubeadm", "token", "create", "--print-join-command", "--ttl", "0"]).decode().strip())



  # Close SSH connection
    ssh.close()

if __name__ == "__main__":
    main()
