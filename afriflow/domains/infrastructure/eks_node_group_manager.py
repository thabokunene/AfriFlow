"""
EKS Node Group Manager for Country Pods.

We manage EKS node groups for each African country pod
in the AfriFlow federated architecture. Each country
requires isolated compute resources for data residency
compliance.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

import boto3
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class NodeGroupStatus(Enum):
    """EKS node group status."""
    CREATING = "CREATING"
    ACTIVE = "ACTIVE"
    DELETING = "DELETING"
    DEGRADED = "DEGRADED"
    CREATE_FAILED = "CREATE_FAILED"


@dataclass
class NodeGroupConfig:
    """
    Configuration for an EKS node group.

    Attributes:
        country_code: ISO 3166-1 alpha-2 country code
        instance_types: List of EC2 instance types
        min_size: Minimum number of nodes
        max_size: Maximum number of nodes
        desired_size: Desired number of nodes
        disk_size_gb: EBS disk size in GB
        subnet_ids: List of subnet IDs
        security_group_ids: List of security group IDs
        iam_role_arn: IAM role ARN for nodes
        labels: Kubernetes labels for nodes
        tags: AWS tags for resources
    """
    country_code: str
    instance_types: List[str] = field(default_factory=list)
    min_size: int = 2
    max_size: int = 10
    desired_size: int = 3
    disk_size_gb: int = 100
    subnet_ids: List[str] = field(default_factory=list)
    security_group_ids: List[str] = field(default_factory=list)
    iam_role_arn: str = ""
    labels: Dict[str, str] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class NodeGroupInfo:
    """
    Information about an EKS node group.

    Attributes:
        name: Node group name
        status: Current status
        desired_nodes: Desired node count
        current_nodes: Current node count
        ready_nodes: Ready node count
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    name: str
    status: NodeGroupStatus
    desired_nodes: int
    current_nodes: int
    ready_nodes: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class EKSNodeGroupManager:
    """
    Manages EKS node groups for AfriFlow country pods.

    We create isolated node groups per country to ensure
    data residency compliance and provide dedicated
    compute resources for each market.

    Attributes:
        cluster_name: EKS cluster name
        region: AWS region
        eks_client: Boto3 EKS client
        autoscaling_client: Boto3 autoscaling client
    """

    # Default instance types by workload type
    INSTANCE_TYPES: Dict[str, List[str]] = {
        "processing": ["m5.2xlarge", "m5.xlarge"],
        "streaming": ["c5.2xlarge", "c5.xlarge"],
        "ingestion": ["m5.xlarge", "m5.large"],
        "monitoring": ["t3.large", "t3.medium"],
    }

    # Country-specific compliance requirements
    COMPLIANCE_REQUIREMENTS: Dict[str, Dict[str, Any]] = {
        "NG": {
            "data_residency": True,
            "encryption_required": True,
            "audit_logging": True,
        },
        "KE": {
            "data_residency": True,
            "encryption_required": True,
            "audit_logging": True,
        },
        "ZA": {
            "data_residency": False,
            "encryption_required": True,
            "audit_logging": True,
        },
    }

    def __init__(
        self,
        cluster_name: str = "afriflow-cluster",
        region: str = "af-south-1"
    ) -> None:
        """
        Initialize the EKS node group manager.

        Args:
            cluster_name: EKS cluster name
            region: AWS region
        """
        self.cluster_name = cluster_name
        self.region = region

        # Initialize AWS clients
        try:
            self.eks_client = boto3.client("eks", region_name=region)
            self.autoscaling_client = boto3.client(
                "autoscaling", region_name=region
            )
            self.ec2_client = boto3.client("ec2", region_name=region)
            logger.info(
                f"EKSNodeGroupManager initialized: "
                f"cluster={cluster_name}, region={region}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize AWS clients: {e}")
            raise

    def create_country_pod_node_group(
        self,
        country_code: str,
        config: Optional[NodeGroupConfig] = None
    ) -> NodeGroupInfo:
        """
        Create an EKS node group for a country pod.

        Args:
            country_code: ISO 3166-1 alpha-2 country code
            config: Optional node group configuration

        Returns:
            NodeGroupInfo with node group details

        Raises:
            ValueError: If country code is invalid
            RuntimeError: If node group creation fails
        """
        country_upper = country_code.upper()

        if not config:
            config = self._get_default_config(country_upper)

        # Validate configuration
        self._validate_config(config)

        # Generate node group name
        node_group_name = f"afriflow-{country_upper.lower()}-ng"

        logger.info(
            f"Creating node group {node_group_name} "
            f"for country {country_upper}"
        )

        try:
            # Prepare create request
            create_params = {
                "clusterName": self.cluster_name,
                "nodegroupName": node_group_name,
                "scalingConfig": {
                    "minSize": config.min_size,
                    "maxSize": config.max_size,
                    "desiredSize": config.desired_size,
                },
                "diskSize": config.disk_size_gb,
                "subnets": config.subnet_ids or self._get_default_subnets(),
                "instanceTypes": config.instance_types,
                "nodeRole": config.iam_role_arn or self._get_default_node_role(),
                "labels": self._get_country_labels(country_upper),
                "tags": self._get_country_tags(country_upper),
            }

            # Add security groups if specified
            if config.security_group_ids:
                create_params["remoteAccess"] = {
                    "ec2SshKey": "afriflow-key",
                    "sourceSecurityGroups": config.security_group_ids,
                }

            # Create node group
            response = self.eks_client.create_nodegroup(**create_params)

            logger.info(
                f"Node group creation initiated: {response['nodegroup']['status']}"
            )

            return NodeGroupInfo(
                name=node_group_name,
                status=NodeGroupStatus.CREATING,
                desired_nodes=config.desired_size,
                current_nodes=0,
                ready_nodes=0,
            )

        except Exception as e:
            logger.error(f"Failed to create node group: {e}")
            raise RuntimeError(
                f"Failed to create node group for {country_upper}: {e}"
            ) from e

    def get_node_group_info(
        self,
        country_code: str
    ) -> Optional[NodeGroupInfo]:
        """
        Get information about a country pod node group.

        Args:
            country_code: ISO 3166-1 alpha-2 country code

        Returns:
            NodeGroupInfo or None if not found
        """
        country_upper = country_code.upper()
        node_group_name = f"afriflow-{country_upper.lower()}-ng"

        try:
            response = self.eks_client.describe_nodegroup(
                clusterName=self.cluster_name,
                nodegroupName=node_group_name,
            )

            ng = response["nodegroup"]

            return NodeGroupInfo(
                name=node_group_name,
                status=NodeGroupStatus(ng["status"]),
                desired_nodes=ng["scalingConfig"]["desiredSize"],
                current_nodes=ng["resources"]["autoScalingGroups"][0][
                    "desiredSize"
                ],
                ready_nodes=ng["resources"]["autoScalingGroups"][0][
                    "desiredSize"
                ],  # Simplified
                created_at=ng["createdAt"],
                updated_at=ng["modifiedAt"],
            )

        except self.eks_client.exceptions.ResourceNotFoundException:
            logger.warning(f"Node group {node_group_name} not found")
            return None
        except Exception as e:
            logger.error(f"Failed to get node group info: {e}")
            raise

    def delete_country_pod_node_group(
        self,
        country_code: str
    ) -> None:
        """
        Delete a country pod node group.

        Args:
            country_code: ISO 3166-1 alpha-2 country code

        Raises:
            RuntimeError: If deletion fails
        """
        country_upper = country_code.upper()
        node_group_name = f"afriflow-{country_upper.lower()}-ng"

        logger.info(f"Deleting node group {node_group_name}")

        try:
            self.eks_client.delete_nodegroup(
                clusterName=self.cluster_name,
                nodegroupName=node_group_name,
            )

            logger.info(f"Node group deletion initiated: {node_group_name}")

        except Exception as e:
            logger.error(f"Failed to delete node group: {e}")
            raise RuntimeError(
                f"Failed to delete node group for {country_upper}: {e}"
            ) from e

    def scale_node_group(
        self,
        country_code: str,
        desired_size: int,
        min_size: Optional[int] = None,
        max_size: Optional[int] = None
    ) -> NodeGroupInfo:
        """
        Scale a country pod node group.

        Args:
            country_code: ISO 3166-1 alpha-2 country code
            desired_size: Desired number of nodes
            min_size: Optional new minimum size
            max_size: Optional new maximum size

        Returns:
            Updated NodeGroupInfo

        Raises:
            RuntimeError: If scaling fails
        """
        country_upper = country_code.upper()
        node_group_name = f"afriflow-{country_upper.lower()}-ng"

        logger.info(
            f"Scaling node group {node_group_name} to {desired_size} nodes"
        )

        try:
            update_params = {
                "clusterName": self.cluster_name,
                "nodegroupName": node_group_name,
                "scalingConfig": {
                    "desiredSize": desired_size,
                },
            }

            if min_size is not None:
                update_params["scalingConfig"]["minSize"] = min_size
            if max_size is not None:
                update_params["scalingConfig"]["maxSize"] = max_size

            self.eks_client.update_nodegroup(**update_params)

            logger.info(f"Node group scaling initiated: {node_group_name}")

            return self.get_node_group_info(country_code) or NodeGroupInfo(
                name=node_group_name,
                status=NodeGroupStatus.ACTIVE,
                desired_nodes=desired_size,
                current_nodes=desired_size,
                ready_nodes=0,
            )

        except Exception as e:
            logger.error(f"Failed to scale node group: {e}")
            raise RuntimeError(
                f"Failed to scale node group for {country_upper}: {e}"
            ) from e

    def list_country_pod_node_groups(self) -> List[NodeGroupInfo]:
        """
        List all country pod node groups.

        Returns:
            List of NodeGroupInfo objects
        """
        node_groups = []

        try:
            response = self.eks_client.list_nodegroups(
                clusterName=self.cluster_name
            )

            for ng_name in response["nodegroups"]:
                if ng_name.startswith("afriflow-"):
                    # Extract country code from name
                    parts = ng_name.split("-")
                    if len(parts) >= 3:
                        country_code = parts[1].upper()
                        info = self.get_node_group_info(country_code)
                        if info:
                            node_groups.append(info)

            return node_groups

        except Exception as e:
            logger.error(f"Failed to list node groups: {e}")
            return []

    def _get_default_config(self, country_code: str) -> NodeGroupConfig:
        """
        Get default configuration for a country.

        Args:
            country_code: ISO 3166-1 alpha-2 country code

        Returns:
            NodeGroupConfig with default values
        """
        # Check compliance requirements
        compliance = self.COMPLIANCE_REQUIREMENTS.get(country_code, {})

        # Adjust instance types based on compliance
        instance_types = self.INSTANCE_TYPES["processing"].copy()

        if compliance.get("data_residency"):
            # Use dedicated instances for data residency
            instance_types = ["m5.2xlarge"]

        return NodeGroupConfig(
            country_code=country_code,
            instance_types=instance_types,
            min_size=2 if compliance.get("data_residency") else 1,
            max_size=10,
            desired_size=3,
            disk_size_gb=100 if compliance.get("encryption_required") else 50,
            labels=self._get_country_labels(country_code),
            tags=self._get_country_tags(country_code),
        )

    def _get_country_labels(self, country_code: str) -> Dict[str, str]:
        """
        Get Kubernetes labels for a country pod.

        Args:
            country_code: ISO 3166-1 alpha-2 country code

        Returns:
            Dictionary of labels
        """
        return {
            "afriflow/country": country_code.lower(),
            "afriflow/region": "africa",
            "afriflow/pod-type": "country",
            "data-residency": "required"
            if self.COMPLIANCE_REQUIREMENTS.get(
                country_code, {}
            ).get("data_residency")
            else "optional",
        }

    def _get_country_tags(self, country_code: str) -> Dict[str, str]:
        """
        Get AWS tags for a country pod.

        Args:
            country_code: ISO 3166-1 alpha-2 country code

        Returns:
            Dictionary of tags
        """
        return {
            "Project": "AfriFlow",
            "Country": country_code,
            "Environment": "production",
            "DataResidency": "required"
            if self.COMPLIANCE_REQUIREMENTS.get(
                country_code, {}
            ).get("data_residency")
            else "optional",
            "ManagedBy": "afriflow-eks-manager",
        }

    def _validate_config(self, config: NodeGroupConfig) -> None:
        """
        Validate node group configuration.

        Args:
            config: Node group configuration

        Raises:
            ValueError: If configuration is invalid
        """
        if config.min_size < 0:
            raise ValueError("min_size must be non-negative")
        if config.max_size < config.min_size:
            raise ValueError("max_size must be >= min_size")
        if config.desired_size < config.min_size:
            raise ValueError("desired_size must be >= min_size")
        if config.desired_size > config.max_size:
            raise ValueError("desired_size must be <= max_size")
        if config.disk_size_gb < 20:
            raise ValueError("disk_size_gb must be >= 20 GB")

    def _get_default_subnets(self) -> List[str]:
        """Get default subnet IDs."""
        # In production, this would query AWS
        return ["subnet-placeholder"]

    def _get_default_node_role(self) -> str:
        """Get default node IAM role ARN."""
        # In production, this would return actual ARN
        return "arn:aws:iam::123456789012:role/afriflow-node-role"


# Convenience function for creating country pod node groups
def create_country_pod(
    country_code: str,
    cluster_name: str = "afriflow-cluster",
    region: str = "af-south-1"
) -> NodeGroupInfo:
    """
    Create an EKS node group for a country pod.

    Args:
        country_code: ISO 3166-1 alpha-2 country code
        cluster_name: EKS cluster name
        region: AWS region

    Returns:
        NodeGroupInfo with node group details
    """
    manager = EKSNodeGroupManager(cluster_name, region)
    return manager.create_country_pod_node_group(country_code)


if __name__ == "__main__":
    # Demo usage
    logging.basicConfig(level=logging.INFO)

    # Create node groups for core markets
    manager = EKSNodeGroupManager()

    for country in ["ZA", "NG", "KE"]:
        try:
            info = manager.create_country_pod_node_group(country)
            print(f"Created {info.name}: {info.status.value}")
        except Exception as e:
            print(f"Failed to create {country}: {e}")
