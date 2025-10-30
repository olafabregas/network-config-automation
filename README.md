# Network Configuration Automation

A professional-grade, secure, and scalable network automation system for configuring and managing network devices using Python, Netmiko, and Jinja2 templates.

## 🚀 Features

- **Secure Credential Management**: Environment-based credential storage using python-dotenv
- **Template-Based Configuration**: Jinja2 templating for flexible, reusable configurations
- **Robust Error Handling**: Comprehensive exception handling and logging
- **Pre/Post Validation**: Built-in validators for configuration verification
- **Parallel Execution**: Support for concurrent device configuration
- **Backup Management**: Automated configuration backup with timestamping
- **Multi-Vendor Support**: Netmiko-based connectivity for multiple device types
- **Comprehensive Testing**: Full test suite with pytest
- **CI/CD Pipeline**: GitHub Actions for automated testing and linting

## 📋 Requirements

- Python 3.9 or higher (tested with 3.9, 3.10, 3.11)
- Network devices accessible via SSH
- Valid credentials for device authentication

## 🔧 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/network-config-automation.git
cd network-config-automation
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

Copy the example environment file and configure your credentials:

```bash
cp .env.example .env
```

Edit `.env` and add your device credentials:

```env
DEVICE_USERNAME=your_username
DEVICE_PASSWORD=your_password
DEVICE_ENABLE_SECRET=your_enable_secret
```

**⚠️ IMPORTANT**: Never commit the `.env` file to version control!

## 📁 Project Structure

```
network-config-automation/
│
├── netauto/                     # Main source package
│   ├── __init__.py              # Package initialization
│   ├── connect.py               # SSH connection handling
│   ├── config_templates.py      # Jinja2 template management
│   ├── tasks.py                 # Automation orchestration
│   ├── validators.py            # Configuration validation
│   ├── logger.py                # Structured logging
│   └── secrets_manager.py       # Credential management
│
├── inventory/                   # Device inventory files
│   └── example_inventory.yml    # Example inventory
│
├── templates/                   # Jinja2 configuration templates
│   ├── base_config.j2           # Base device configuration
│   └── ospf_config.j2           # OSPF routing configuration
│
├── tests/                       # Test suite
│   ├── conftest.py              # Pytest configuration
│   ├── test_connect.py          # Connection tests
│   └── test_tasks.py            # Task orchestration tests
│
├── .github/workflows/           # CI/CD pipelines
│   └── ci.yml                   # GitHub Actions workflow
│
├── cli.py                       # Command-line interface
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment template
├── .gitignore                   # Git ignore rules
└── README.md                    # This file
```

## 🎯 Quick Start

### Using the CLI

```bash
# Configure a single device
python cli.py configure --host 192.168.1.1 --template base_config.j2

# Configure multiple devices from inventory
python cli.py configure-inventory --inventory inventory/example_inventory.yml

# Backup device configurations
python cli.py backup --host 192.168.1.1 --output backups/

# Run validation checks
python cli.py validate --host 192.168.1.1
```

### Using Python API

```python
from netauto import NetworkDevice, ConfigurationTask

# Connect to a single device
with NetworkDevice(host="192.168.1.1", device_type="cisco_ios") as device:
    output = device.send_command("show version")
    print(output)

# Configure multiple devices
devices = [
    {"host": "192.168.1.1", "device_type": "cisco_ios"},
    {"host": "192.168.1.2", "device_type": "cisco_ios"},
]

task = ConfigurationTask(devices=devices)
result = task.configure_multiple_devices(
    config_commands=["hostname ROUTER-01", "no ip domain-lookup"],
    save_config=True,
    validate_after=True,
    parallel=True,
)

print(f"Success: {result['successful']}/{result['total_devices']}")
```

## 📝 Configuration Templates

Templates use Jinja2 syntax for dynamic configuration generation:

```jinja2
hostname {{ hostname }}
!
ip domain-name {{ domain_name }}
!
{% for ntp_server in ntp_servers %}
ntp server {{ ntp_server }}
{% endfor %}
!
```

Example template variables:

```python
template_vars = {
    "hostname": "CORE-SW-01",
    "domain_name": "company.local",
    "ntp_servers": ["10.0.0.1", "10.0.0.2"],
}
```

## ✅ Validation

The validation system supports multiple check types:

```python
from netauto import NetworkDevice, ConfigValidator

device = NetworkDevice(host="192.168.1.1")
device.connect()

validator = ConfigValidator(device)

# Basic connectivity
validator.verify_connectivity()

# Interface status
validator.verify_interface_status("GigabitEthernet0/1", "up")

# Routing protocol
validator.verify_routing_protocol("ospf")

# IP connectivity
validator.verify_ip_connectivity("192.168.1.254")

device.disconnect()
```

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=netauto --cov-report=html

# Run specific test file
pytest tests/test_connect.py -v

# Run specific test
pytest tests/test_connect.py::TestNetworkDevice::test_successful_connection -v
```

## 🔒 Security Best Practices

1. **Never commit credentials** - Use environment variables or `.env` files
2. **Use strong passwords** - Implement password policies
3. **Enable SSH key authentication** - When possible, prefer key-based auth
4. **Limit access** - Use principle of least privilege
5. **Audit logs** - Review logs regularly for suspicious activity
6. **Keep dependencies updated** - Regularly update packages for security patches
7. **Use VPN/Jump hosts** - For production environments, use secure access methods

## 📊 Logging

Logs are configurable via environment variables:

```env
LOG_LEVEL=INFO
LOG_FILE=logs/netauto.log
LOG_JSON_FORMAT=false
```

Example log output:

```
2024-10-30 10:15:30 - netauto.connect - INFO - Connecting to 192.168.1.1...
2024-10-30 10:15:32 - netauto.connect - INFO - Successfully connected to 192.168.1.1
2024-10-30 10:15:35 - netauto.tasks - INFO - Configuration applied successfully on 192.168.1.1
```

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style

- Follow PEP 8 guidelines
- Use Black for code formatting: `black netauto tests`
- Run linting: `flake8 netauto`
- Ensure tests pass: `pytest`

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Netmiko**: Network device SSH connection library
- **Paramiko**: Low-level SSH implementation
- **Jinja2**: Powerful templating engine
- **pytest**: Comprehensive testing framework

## 📞 Support

For issues, questions, or contributions:

- **Issues**: [GitHub Issues](https://github.com/yourusername/network-config-automation/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/network-config-automation/discussions)
- **Email**: support@example.com

## 🗺️ Roadmap

- [ ] Add support for REST API-based devices (RESTCONF/NETCONF)
- [ ] Implement configuration diffing and rollback
- [ ] Add web-based UI dashboard
- [ ] Support for Ansible inventory format
- [ ] Integration with version control for config management
- [ ] Real-time device monitoring and alerting
- [ ] Multi-tenancy support
- [ ] Database backend for audit logging

## 📚 Additional Resources

- [Netmiko Documentation](https://github.com/ktbyers/netmiko)
- [Jinja2 Documentation](https://jinja.palletsprojects.com/)
- [Network Automation Best Practices](https://www.networkautomation.io/)

---

**Built with ❤️ for Network Engineers**
