"""A Python Pulumi program"""

from dataclasses import dataclass

import pulumi
import pulumi_pulumiservice as pulumiservice
from pulumi_aws import ecs


@dataclass
class ClusterArgs:
    teams: list[str]

class Cluster(pulumi.ComponentResource):
    def __init__(self, name: str, args: ClusterArgs, opts: pulumi.ResourceOptions):
        super().__init__("nytro:services:Cluster", name, None, opts)
        self.teams = args.teams

        pulumi_org = pulumi.get_organization()
        pulumi_project = pulumi.get_project()
        pulumi_stack = pulumi.get_stack()

        cluster = ecs.Cluster(
            "cluster",
            opts=pulumi.ResourceOptions(
                parent=self,
            ),
        )

        self.cluster_arn = cluster.arn

        env_yaml = pulumi.Output.format(
            """
            values:
                pulumiConfig:
                    cluster_arn: {0}
            """,
            cluster.arn,
        )

        env = pulumiservice.Environment(
            "cluster-env",
            name=f"{pulumi_stack}",
            organization=pulumi_org,
            project=pulumi_project,
            yaml=env_yaml.apply(pulumi.StringAsset),
            opts=pulumi.ResourceOptions(parent=self),
)

        for team in args.teams:
            pulumiservice.TeamEnvironmentPermission(
                f"cluster-{team}-env-perm",
                environment=env.name,
                organization=pulumi_org,
                permission=pulumiservice.EnvironmentPermission.OPEN,
                team=team,
                project=pulumi_project,
                opts=pulumi.ResourceOptions(
                    parent=self,
                ),
            )

        self.env_name = pulumi.Output.format(
            "{0}/{1}", pulumi_project, env.name)

        self.register_outputs({
            "cluster_arn": self.cluster_arn,
            "env_name": self.env_name,
        })
