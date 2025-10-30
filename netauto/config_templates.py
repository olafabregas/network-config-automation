"""
Config Templates - Manages Jinja2 configuration templates.
Provides template rendering with device-specific variables.
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, Template, TemplateNotFound
from .logger import setup_logger


logger = setup_logger("netauto.templates")


class TemplateManager:
    """Manages configuration templates using Jinja2."""
    
    def __init__(self, template_dir: Optional[str] = None):
        """
        Initialize the template manager.
        
        Args:
            template_dir: Path to templates directory. If None, uses default.
        """
        if template_dir:
            self.template_dir = Path(template_dir)
        else:
            self.template_dir = Path(__file__).parent.parent / "templates"
        
        if not self.template_dir.exists():
            logger.warning(f"Template directory does not exist: {self.template_dir}")
            self.template_dir.mkdir(parents=True, exist_ok=True)
        
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        
        logger.info(f"Template manager initialized with directory: {self.template_dir}")
    
    def render_template(
        self,
        template_name: str,
        variables: Dict[str, Any],
    ) -> str:
        """
        Render a template with provided variables.
        
        Args:
            template_name: Name of the template file
            variables: Dictionary of template variables
            
        Returns:
            Rendered configuration as string
            
        Raises:
            TemplateNotFound: If template file doesn't exist
            Exception: If template rendering fails
        """
        try:
            template = self.env.get_template(template_name)
            rendered = template.render(**variables)
            logger.info(f"Successfully rendered template: {template_name}")
            return rendered
            
        except TemplateNotFound:
            error_msg = f"Template not found: {template_name}"
            logger.error(error_msg)
            raise
            
        except Exception as e:
            error_msg = f"Error rendering template {template_name}: {str(e)}"
            logger.error(error_msg)
            raise
    
    def render_string(
        self,
        template_string: str,
        variables: Dict[str, Any],
    ) -> str:
        """
        Render a template from a string.
        
        Args:
            template_string: Template content as string
            variables: Dictionary of template variables
            
        Returns:
            Rendered configuration as string
        """
        try:
            template = Template(template_string)
            rendered = template.render(**variables)
            logger.debug("Successfully rendered template from string")
            return rendered
            
        except Exception as e:
            error_msg = f"Error rendering template string: {str(e)}"
            logger.error(error_msg)
            raise
    
    def list_templates(self) -> List[str]:
        """
        List all available templates.
        
        Returns:
            List of template filenames
        """
        templates: List[str] = [f.name for f in self.template_dir.glob("*.j2")]
        logger.debug(f"Found {len(templates)} templates")
        return templates
    
    def get_template_path(self, template_name: str) -> Path:
        """
        Get the full path to a template file.
        
        Args:
            template_name: Name of the template
            
        Returns:
            Path object for the template
        """
        return self.template_dir / template_name


# Predefined template configurations
BASE_CONFIG_TEMPLATE = """
hostname {{ hostname }}
!
{{ banner }}
!
no ip domain-lookup
ip domain-name {{ domain_name }}
!
{% if ntp_servers %}
{% for ntp_server in ntp_servers %}
ntp server {{ ntp_server }}
{% endfor %}
{% endif %}
!
{% if name_servers %}
{% for name_server in name_servers %}
ip name-server {{ name_server }}
{% endfor %}
{% endif %}
!
line con 0
 logging synchronous
 exec-timeout {{ console_timeout }}
line vty 0 4
 login local
 transport input ssh
 exec-timeout {{ vty_timeout }}
!
end
"""


OSPF_CONFIG_TEMPLATE = """
router ospf {{ process_id }}
 router-id {{ router_id }}
{% if passive_interfaces %}
{% for interface in passive_interfaces %}
 passive-interface {{ interface }}
{% endfor %}
{% endif %}
{% if networks %}
{% for network in networks %}
 network {{ network.address }} {{ network.wildcard }} area {{ network.area }}
{% endfor %}
{% endif %}
{% if default_information %}
 default-information originate
{% endif %}
!
end
"""


def get_base_config(variables: Dict[str, Any]) -> str:
    """
    Generate base device configuration.
    
    Args:
        variables: Configuration variables
        
    Returns:
        Rendered configuration string
    """
    manager = TemplateManager()
    return manager.render_string(BASE_CONFIG_TEMPLATE, variables)


def get_ospf_config(variables: Dict[str, Any]) -> str:
    """
    Generate OSPF configuration.
    
    Args:
        variables: OSPF configuration variables
        
    Returns:
        Rendered configuration string
    """
    manager = TemplateManager()
    return manager.render_string(OSPF_CONFIG_TEMPLATE, variables)
