"""Parse CloudFormation YAML and emit Terraform aligned with Pattern Catalogue workflows."""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Any

import yaml

from .local_workspace_tools import write_local_workspace_file

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _snake(name: str) -> str:
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def _cfn_allowed_roots() -> list[Path]:
    roots = [_PROJECT_ROOT.resolve(), (_PROJECT_ROOT / "agent_output").resolve()]
    raw = (Path(__file__).resolve().parent.parent / ".env")  # noqa: F841
    import os

    extra = (os.environ.get("CFN_CONVERT_ALLOWED_ROOTS") or "").strip()
    if extra:
        for part in extra.split(","):
            p = part.strip()
            if p:
                roots.append(Path(p).expanduser().resolve())
    return roots


def _is_allowed_path(path: Path, roots: list[Path]) -> bool:
    try:
        resolved = path.resolve()
    except OSError:
        return False
    for root in roots:
        try:
            resolved.relative_to(root)
            return True
        except ValueError:
            continue
    return False


class _CfnLoader(yaml.SafeLoader):
    pass


def _construct_ref(loader: yaml.Loader, node: yaml.Node) -> dict[str, Any]:
    return {"Ref": loader.construct_scalar(node)}


def _construct_sub(loader: yaml.Loader, node: yaml.Node) -> Any:
    if isinstance(node, yaml.ScalarNode):
        return {"Fn::Sub": loader.construct_scalar(node)}
    seq = loader.construct_sequence(node)
    if len(seq) == 2 and isinstance(seq[1], dict):
        return {"Fn::Sub": [seq[0], seq[1]]}
    return {"Fn::Sub": seq}


def _construct_getatt(loader: yaml.Loader, node: yaml.Node) -> dict[str, Any]:
    if isinstance(node, yaml.ScalarNode):
        s = loader.construct_scalar(node)
        if "." in s:
            lid, attr = s.split(".", 1)
            return {"Fn::GetAtt": [lid, attr]}
        return {"Fn::GetAtt": [s, ""]}
    seq = loader.construct_sequence(node)
    if len(seq) == 2:
        return {"Fn::GetAtt": [seq[0], seq[1]]}
    return {"Fn::GetAtt": seq}


def _construct_join(loader: yaml.Loader, node: yaml.Node) -> dict[str, Any]:
    seq = loader.construct_sequence(node)
    return {"Fn::Join": seq}


_CfnLoader.add_constructor("!Ref", _construct_ref)
_CfnLoader.add_constructor("!Sub", _construct_sub)
_CfnLoader.add_constructor("!GetAtt", _construct_getatt)
_CfnLoader.add_constructor("!Join", _construct_join)


def _load_cfn_template(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    data = yaml.load(text, Loader=_CfnLoader)
    if not isinstance(data, dict):
        raise ValueError("Template root must be a mapping.")
    return data


# Terraform attribute to use for Ref() per CloudFormation resource type
_REF_ATTR: dict[str, str] = {
    "AWS::ECS::Cluster": "name",
    "AWS::ECS::TaskDefinition": "arn",
    "AWS::ECS::Service": "id",
    "AWS::IAM::Role": "arn",
    "AWS::Logs::LogGroup": "name",
    "AWS::EC2::SecurityGroup": "id",
    "AWS::ElasticLoadBalancingV2::LoadBalancer": "arn",
    "AWS::ElasticLoadBalancingV2::TargetGroup": "arn",
    "AWS::ElasticLoadBalancingV2::Listener": "arn",
}


def _tf_resource_type(cfn_type: str) -> str | None:
    return {
        "AWS::ECS::Cluster": "aws_ecs_cluster",
        "AWS::Logs::LogGroup": "aws_cloudwatch_log_group",
        "AWS::IAM::Role": "aws_iam_role",
        "AWS::EC2::SecurityGroup": "aws_security_group",
        "AWS::ElasticLoadBalancingV2::LoadBalancer": "aws_lb",
        "AWS::ElasticLoadBalancingV2::TargetGroup": "aws_lb_target_group",
        "AWS::ElasticLoadBalancingV2::Listener": "aws_lb_listener",
        "AWS::ECS::TaskDefinition": "aws_ecs_task_definition",
        "AWS::ECS::Service": "aws_ecs_service",
    }.get(cfn_type)


def _param_tf_type(param_spec: dict[str, Any]) -> str:
    t = (param_spec.get("Type") or "String").strip()
    if t.startswith("List<"):
        return "list(string)"
    if t == "Number":
        return "number"
    return "string"


def _resolve_to_expr(
    val: Any,
    *,
    parameters: dict[str, Any],
    logical_to_tf: dict[str, str],
    logical_to_cfn_type: dict[str, str],
    stack_var: str,
) -> str:
    if val is None:
        return "null"
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, int | float):
        return str(val)
    if isinstance(val, str):
        return json.dumps(val)
    if isinstance(val, dict):
        if "Ref" in val:
            r = val["Ref"]
            if r == "AWS::Region":
                return "data.aws_region.current.name"
            if r == "AWS::AccountId":
                return "data.aws_caller_identity.current.account_id"
            if r == "AWS::StackName":
                return f"var.{stack_var}"
            if r in parameters:
                return f"var.{_snake(r)}"
            if r in logical_to_tf:
                cfn_t = logical_to_cfn_type.get(r, "")
                attr = _REF_ATTR.get(cfn_t, "id")
                tf_t = logical_to_tf[r]
                return f"{_tf_resource_type(cfn_t) or 'aws_resource'}.{tf_t}.{attr}"
            return json.dumps(f"UNKNOWN_REF_{r}")
        if "Fn::GetAtt" in val:
            ga = val["Fn::GetAtt"]
            if isinstance(ga, list) and len(ga) >= 2:
                lid, attr = ga[0], ga[1]
            else:
                return json.dumps(val)
            tf_n = logical_to_tf.get(lid, _snake(lid))
            cfn_t = logical_to_cfn_type.get(lid, "")
            attr_map = {
                ("AWS::ElasticLoadBalancingV2::LoadBalancer", "DNSName"): "dns_name",
                ("AWS::ElasticLoadBalancingV2::LoadBalancer", "LoadBalancerFullName"): "name",
                ("AWS::ECS::Service", "Name"): "name",
            }
            tf_attr = attr_map.get((cfn_t, attr), _snake(attr))
            rt = _tf_resource_type(cfn_t) or "aws_resource"
            return f"{rt}.{tf_n}.{tf_attr}"
        if "Fn::Sub" in val:
            sub = val["Fn::Sub"]
            if isinstance(sub, list) and len(sub) == 2:
                template, _vars = sub[0], sub[1]
            else:
                template = sub
            return _interpolate_sub(
                str(template),
                parameters=parameters,
                logical_to_tf=logical_to_tf,
                logical_to_cfn_type=logical_to_cfn_type,
                stack_var=stack_var,
            )
        if "Fn::Join" in val:
            parts = val["Fn::Join"]
            if isinstance(parts, list) and len(parts) == 2:
                delim, seq = parts[0], parts[1]
                inner = [
                    _resolve_to_expr(
                        x,
                        parameters=parameters,
                        logical_to_tf=logical_to_tf,
                        logical_to_cfn_type=logical_to_cfn_type,
                        stack_var=stack_var,
                    )
                    for x in seq
                ]
                return f"join({json.dumps(delim)}, [{', '.join(inner)}])"
            return json.dumps(val)
        return json.dumps(val)
    if isinstance(val, list):
        elems = [
            _resolve_to_expr(
                x,
                parameters=parameters,
                logical_to_tf=logical_to_tf,
                logical_to_cfn_type=logical_to_cfn_type,
                stack_var=stack_var,
            )
            for x in val
        ]
        return "[\n    " + ",\n    ".join(elems) + "\n  ]"
    return json.dumps(val)


def _interpolate_sub(
    template: str,
    *,
    parameters: dict[str, Any],
    logical_to_tf: dict[str, str],
    logical_to_cfn_type: dict[str, str],
    stack_var: str,
) -> str:
    """Turn CFN ${Var} sub strings into Terraform "${ ... }" fragments."""

    def repl(m: re.Match[str]) -> str:
        inner = m.group(1)
        if inner == "AWS::Region":
            return "${data.aws_region.current.name}"
        if inner == "AWS::AccountId":
            return "${data.aws_caller_identity.current.account_id}"
        if inner == "AWS::StackName":
            return f"${{var.{stack_var}}}"
        if inner in parameters:
            return f"${{var.{_snake(inner)}}}"
        if inner in logical_to_tf:
            cfn_t = logical_to_cfn_type.get(inner, "")
            attr = _REF_ATTR.get(cfn_t, "id")
            tf_t = logical_to_tf[inner]
            rt = _tf_resource_type(cfn_t) or "aws_resource"
            return f"${{{rt}.{tf_t}.{attr}}}"
        return "${" + inner + "}"

    out = re.sub(r"\$\{([^}]+)\}", repl, template)
    return json.dumps(out)


def _collect_parameters(template: dict[str, Any]) -> dict[str, Any]:
    params = template.get("Parameters") or {}
    return params if isinstance(params, dict) else {}


def _build_logical_maps(resources: dict[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
    logical_to_tf: dict[str, str] = {}
    logical_to_cfn_type: dict[str, str] = {}
    for lid, spec in resources.items():
        if not isinstance(spec, dict):
            continue
        cfn_t = spec.get("Type")
        if not cfn_t:
            continue
        logical_to_cfn_type[lid] = str(cfn_t)
        logical_to_tf[lid] = _snake(lid)
    return logical_to_tf, logical_to_cfn_type


def _emit_variables_tf(parameters: dict[str, Any], stack_var: str) -> str:
    lines: list[str] = [
        "# Generated from CloudFormation Parameters.",
        f'variable "{stack_var}" {{',
        "  type        = string",
        '  description = "Stack name placeholder (maps to AWS::StackName in Sub/Ref)."',
        '  default     = "cfn-stack"',
        "}",
        "",
    ]
    for name, spec in parameters.items():
        if not isinstance(spec, dict):
            continue
        sn = _snake(name)
        desc = (spec.get("Description") or "").strip().replace('"', "'")
        ptype = _param_tf_type(spec)
        lines.append(f'variable "{sn}" {{')
        lines.append(f"  type        = {ptype}")
        if desc:
            lines.append(f'  description = "{desc}"')
        if "Default" in spec:
            d = spec["Default"]
            if ptype == "string":
                lines.append(f"  default     = {json.dumps(str(d))}")
            elif ptype == "number":
                lines.append(f"  default     = {d}")
            else:
                lines.append(f"  default     = {json.dumps(d)}")
        lines.append("}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _emit_provider_block() -> str:
    return """terraform {
  required_version = ">= 1.3.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_region" "current" {}
data "aws_caller_identity" "current" {}
"""


def _unsupported_resource_block(logical_id: str, cfn_type: str, props: Any) -> str:
    return f"""# TODO: Unsupported or manual mapping for {logical_id} ({cfn_type})
# Raw Properties (trimmed JSON):
# {json.dumps(props, indent=2)[:4000]}
"""


async def convert_cloudformation_template_to_terraform(
    cloudformation_template_path: str,
    output_relative_directory: str = "terraform/cfn-converted",
    stack_name_variable: str = "stack_name",
    write_pattern_catalog_readme: bool = True,
) -> dict[str, Any]:
    """Read a CloudFormation template (YAML) and write Terraform files to the agent output directory.

    Parses Parameters and Resources that this tool knows how to map (ECS, ALB, IAM, logs, SG).
    Emits ``main.tf``, ``variables.tf``, ``outputs.tf`` (``versions.tf`` fragment lives in main),
    ``README.md``, plus optional ``PATTERN_CATALOG.md`` with steps to align resources using Pattern Catalogue MCP tools.

    The Pattern Catalogue is **not** invoked from Python (MCP is available to the LLM at runtime).
    After conversion, use Pattern Catalogue MCP tools to replace ``aws_*`` resources with approved
    internal modules and adjust ``source`` / inputs per your organization.

    Args:
        cloudformation_template_path: Absolute path to ``.yaml`` / ``.yml`` template on disk
            (must be under the project root, ``agent_output/``, or ``CFN_CONVERT_ALLOWED_ROOTS``).
        output_relative_directory: Directory relative to the agent output root (e.g.
            ``terraform/my-ecs``). Files are created inside this directory.
        stack_name_variable: Terraform variable name for ``AWS::StackName`` (default ``stack_name``).
        write_pattern_catalog_readme: If True, writes ``PATTERN_CATALOG.md`` with MCP workflow hints.

    Returns:
        Status dict: ok, paths written, resource summary, pattern_catalog_hints, or error.
    """
    roots = _cfn_allowed_roots()
    src = Path(cloudformation_template_path).expanduser()
    if not _is_allowed_path(src, roots):
        return {
            "ok": False,
            "error": (
                "Template path must be under the project root, agent_output/, or "
                "CFN_CONVERT_ALLOWED_ROOTS (comma-separated absolute paths)."
            ),
            "path": str(src),
        }
    if not src.is_file():
        return {"ok": False, "error": f"Not a file: {src}"}

    try:
        template = _load_cfn_template(src)
    except Exception as e:
        return {"ok": False, "error": f"Failed to parse YAML: {e}"}

    parameters = _collect_parameters(template)
    resources_raw = template.get("Resources") or {}
    if not isinstance(resources_raw, dict):
        return {"ok": False, "error": "Template has no Resources mapping."}

    logical_to_tf, logical_to_cfn_type = _build_logical_maps(resources_raw)
    stack_var = _snake(stack_name_variable) if stack_name_variable else "stack_name"

    # --- Build main.tf body (resource-by-resource, simplified emitters) ---
    main_parts: list[str] = [
        "# Generated from CloudFormation. Review before apply.",
        "# Replace with Pattern Catalogue modules where your MCP provides approved sources.",
        "",
        _emit_provider_block(),
        "",
    ]

    supported: list[str] = []
    skipped: list[str] = []

    ctx = {
        "parameters": parameters,
        "logical_to_tf": logical_to_tf,
        "logical_to_cfn_type": logical_to_cfn_type,
        "stack_var": stack_var,
    }

    for lid, spec in resources_raw.items():
        if not isinstance(spec, dict):
            continue
        cfn_type = spec.get("Type")
        props = spec.get("Properties") or {}
        if not cfn_type:
            continue
        tf_name = logical_to_tf[lid]
        rt = _tf_resource_type(str(cfn_type))

        if rt == "aws_ecs_cluster" and isinstance(props, dict):
            name_expr = _resolve_to_expr(props.get("ClusterName"), **ctx)
            main_parts.append(f'resource "aws_ecs_cluster" "{tf_name}" {{')
            main_parts.append(f"  name = {name_expr}")
            if props.get("ClusterSettings"):
                main_parts.append("  setting {")
                main_parts.append('    name  = "containerInsights"')
                main_parts.append('    value = "enabled"')
                main_parts.append("  }")
            main_parts.append("}")
            main_parts.append("")
            supported.append(f"{lid} ({cfn_type})")
            continue

        if rt == "aws_cloudwatch_log_group" and isinstance(props, dict):
            main_parts.append(f'resource "aws_cloudwatch_log_group" "{tf_name}" {{')
            main_parts.append(f"  name              = {_resolve_to_expr(props.get('LogGroupName'), **ctx)}")
            if props.get("RetentionInDays") is not None:
                main_parts.append(f"  retention_in_days = {props['RetentionInDays']}")
            main_parts.append("}")
            main_parts.append("")
            supported.append(f"{lid} ({cfn_type})")
            continue

        if rt == "aws_iam_role" and isinstance(props, dict):
            main_parts.append(f'resource "aws_iam_role" "{tf_name}" {{')
            if props.get("RoleName"):
                main_parts.append(f"  name = {_resolve_to_expr(props['RoleName'], **ctx)}")
            main_parts.append('  assume_role_policy = jsonencode(')
            main_parts.append(json.dumps(props.get("AssumeRolePolicyDocument") or {}, indent=4))
            main_parts.append("  )")
            mpa = props.get("ManagedPolicyArns") or []
            if isinstance(mpa, list):
                arns = [p for p in mpa if isinstance(p, str)]
                if arns:
                    main_parts.append(f"  managed_policy_arns = {json.dumps(arns)}")
            main_parts.append("}")
            main_parts.append("")
            supported.append(f"{lid} ({cfn_type})")
            continue

        if rt == "aws_security_group" and isinstance(props, dict):
            main_parts.append(f'resource "aws_security_group" "{tf_name}" {{')
            main_parts.append(f"  description = {_resolve_to_expr(props.get('GroupDescription', lid), **ctx)}")
            main_parts.append(f"  vpc_id      = {_resolve_to_expr(props.get('VpcId'), **ctx)}")
            ingress = props.get("SecurityGroupIngress") or []
            if isinstance(ingress, list):
                for rule in ingress:
                    if not isinstance(rule, dict):
                        continue
                    main_parts.append("  ingress {")
                    main_parts.append(f"    from_port   = {_resolve_to_expr(rule.get('FromPort'), **ctx)}")
                    main_parts.append(f"    to_port     = {_resolve_to_expr(rule.get('ToPort'), **ctx)}")
                    main_parts.append(f"    protocol    = {json.dumps(rule.get('IpProtocol', 'tcp'))}")
                    if rule.get("CidrIp"):
                        main_parts.append(f"    cidr_blocks = [{_resolve_to_expr(rule['CidrIp'], **ctx)}]")
                    if rule.get("SourceSecurityGroupId"):
                        main_parts.append(
                            f"    security_groups = [{_resolve_to_expr(rule['SourceSecurityGroupId'], **ctx)}]"
                        )
                    main_parts.append("  }")
            main_parts.append("}")
            main_parts.append("")
            supported.append(f"{lid} ({cfn_type})")
            continue

        if rt == "aws_lb" and isinstance(props, dict):
            main_parts.append(f'resource "aws_lb" "{tf_name}" {{')
            main_parts.append(f"  name               = {_resolve_to_expr(props.get('Name'), **ctx)}")
            main_parts.append(f"  internal           = {str(props.get('Scheme') == 'internal').lower()}")
            main_parts.append(f"  load_balancer_type = {json.dumps(props.get('Type', 'application'))}")
            main_parts.append(f"  subnets            = {_resolve_to_expr(props.get('Subnets'), **ctx)}")
            sgs = props.get("SecurityGroups") or []
            if isinstance(sgs, list) and sgs:
                exprs = [_resolve_to_expr(s, **ctx) for s in sgs]
                main_parts.append(f"  security_groups    = [{', '.join(exprs)}]")
            main_parts.append("}")
            main_parts.append("")
            supported.append(f"{lid} ({cfn_type})")
            continue

        if rt == "aws_lb_target_group" and isinstance(props, dict):
            main_parts.append(f'resource "aws_lb_target_group" "{tf_name}" {{')
            main_parts.append(f"  name        = {_resolve_to_expr(props.get('Name'), **ctx)}")
            main_parts.append(f"  port        = {_resolve_to_expr(props.get('Port'), **ctx)}")
            main_parts.append(f"  protocol    = {json.dumps(props.get('Protocol', 'HTTP'))}")
            main_parts.append(f"  vpc_id      = {_resolve_to_expr(props.get('VpcId'), **ctx)}")
            main_parts.append(f"  target_type = {json.dumps(props.get('TargetType', 'ip'))}")
            if props.get("HealthCheckPath"):
                main_parts.append(f"  health_check {{")
                main_parts.append(f"    path = {json.dumps(props['HealthCheckPath'])}")
                main_parts.append("  }")
            main_parts.append("}")
            main_parts.append("")
            supported.append(f"{lid} ({cfn_type})")
            continue

        if rt == "aws_lb_listener" and isinstance(props, dict):
            acts = props.get("DefaultActions") or []
            tg_arn = "null"
            if isinstance(acts, list) and acts:
                a0 = acts[0]
                if isinstance(a0, dict) and a0.get("Type") == "forward":
                    tg_arn = _resolve_to_expr(a0.get("TargetGroupArn"), **ctx)
            main_parts.append(f'resource "aws_lb_listener" "{tf_name}" {{')
            main_parts.append(f"  load_balancer_arn = {_resolve_to_expr(props.get('LoadBalancerArn'), **ctx)}")
            main_parts.append(f"  port              = {_resolve_to_expr(props.get('Port'), **ctx)}")
            main_parts.append(f"  protocol          = {json.dumps(props.get('Protocol', 'HTTP'))}")
            main_parts.append("  default_action {")
            main_parts.append('    type             = "forward"')
            main_parts.append(f"    target_group_arn = {tg_arn}")
            main_parts.append("  }")
            main_parts.append("}")
            main_parts.append("")
            supported.append(f"{lid} ({cfn_type})")
            continue

        if rt == "aws_ecs_task_definition" and isinstance(props, dict):
            cds = props.get("ContainerDefinitions") or []
            main_parts.append(f'resource "aws_ecs_task_definition" "{tf_name}" {{')
            main_parts.append(f"  family                   = {_resolve_to_expr(props.get('Family'), **ctx)}")
            main_parts.append(f"  requires_compatibilities = {json.dumps(props.get('RequiresCompatibilities') or ['FARGATE'])}")
            main_parts.append(f"  network_mode             = {json.dumps(props.get('NetworkMode', 'awsvpc'))}")
            main_parts.append(f"  cpu                      = {_resolve_to_expr(props.get('Cpu'), **ctx)}")
            main_parts.append(f"  memory                   = {_resolve_to_expr(props.get('Memory'), **ctx)}")
            main_parts.append(f"  execution_role_arn       = {_resolve_to_expr(props.get('ExecutionRoleArn'), **ctx)}")
            if props.get("TaskRoleArn"):
                main_parts.append(f"  task_role_arn            = {_resolve_to_expr(props['TaskRoleArn'], **ctx)}")
            # container_definitions: resolve nested
            if isinstance(cds, list) and cds and isinstance(cds[0], dict):
                c0 = cds[0]
                port_maps = c0.get("PortMappings") or []
                pm = port_maps[0] if port_maps and isinstance(port_maps[0], dict) else {}
                img = _resolve_to_expr(c0.get("Image"), **ctx)
                cport = _resolve_to_expr(pm.get("ContainerPort"), **ctx) if pm else "80"
                log_opts = ((c0.get("LogConfiguration") or {}).get("Options") or {})
                lg_e = (
                    _resolve_to_expr(log_opts.get("awslogs-group"), **ctx)
                    if isinstance(log_opts, dict)
                    else '""'
                )
                reg_e = (
                    _resolve_to_expr(log_opts.get("awslogs-region"), **ctx)
                    if isinstance(log_opts, dict)
                    else "data.aws_region.current.name"
                )
                stream = json.dumps(
                    (log_opts.get("awslogs-stream-prefix", "ecs") if isinstance(log_opts, dict) else "ecs")
                )
                cname = json.dumps(c0.get("Name", "app"))
                main_parts.append("  container_definitions = jsonencode([")
                main_parts.append("    {")
                main_parts.append(f"      name      = {cname}")
                main_parts.append(f"      image     = {img}")
                main_parts.append(f"      essential = {str(c0.get('Essential', True)).lower()}")
                main_parts.append(
                    f"      portMappings = [{{ containerPort = {cport}, protocol = \"tcp\" }}]"
                )
                main_parts.append("      logConfiguration = {")
                main_parts.append('        logDriver = "awslogs"')
                main_parts.append("        options = {")
                main_parts.append(f'          "awslogs-group"         = {lg_e}')
                main_parts.append(f'          "awslogs-region"        = {reg_e}')
                main_parts.append(f'          "awslogs-stream-prefix" = {stream}')
                main_parts.append("        }")
                main_parts.append("      }")
                main_parts.append("    }")
                main_parts.append("  ])")
            main_parts.append("}")
            main_parts.append("")
            supported.append(f"{lid} ({cfn_type})")
            continue

        if rt == "aws_ecs_service" and isinstance(props, dict):
            dep = spec.get("DependsOn")
            main_parts.append(f'resource "aws_ecs_service" "{tf_name}" {{')
            if dep:
                if isinstance(dep, str):
                    dep_tf = logical_to_tf.get(dep, _snake(dep))
                    main_parts.append(f"  depends_on = [aws_lb_listener.{dep_tf}]")
                elif isinstance(dep, list):
                    deps = [f"aws_lb_listener.{logical_to_tf.get(d, _snake(d))}" for d in dep]
                    main_parts.append(f"  depends_on = [{', '.join(deps)}]")
            main_parts.append(f"  name            = {_resolve_to_expr(props.get('ServiceName'), **ctx)}")
            main_parts.append(f"  cluster         = {_resolve_to_expr(props.get('Cluster'), **ctx)}")
            main_parts.append(f"  task_definition = {_resolve_to_expr(props.get('TaskDefinition'), **ctx)}")
            main_parts.append(f"  desired_count   = {_resolve_to_expr(props.get('DesiredCount'), **ctx)}")
            main_parts.append(f"  launch_type     = {json.dumps(props.get('LaunchType', 'FARGATE'))}")
            nc = props.get("NetworkConfiguration") or {}
            awsvpc = (nc.get("AwsvpcConfiguration") or {}) if isinstance(nc, dict) else {}
            if awsvpc:
                main_parts.append("  network_configuration {")
                main_parts.append(
                    f"    assign_public_ip = {str(awsvpc.get('AssignPublicIp') == 'ENABLED').lower()}"
                )
                main_parts.append(f"    subnets          = {_resolve_to_expr(awsvpc.get('Subnets'), **ctx)}")
                sgs = awsvpc.get("SecurityGroups") or []
                if isinstance(sgs, list) and sgs:
                    exprs = [_resolve_to_expr(s, **ctx) for s in sgs]
                    main_parts.append(f"    security_groups  = [{', '.join(exprs)}]")
                main_parts.append("  }")
            lbs = props.get("LoadBalancers") or []
            if isinstance(lbs, list) and lbs:
                lb0 = lbs[0]
                if isinstance(lb0, dict):
                    main_parts.append("  load_balancer {")
                    main_parts.append(f"    target_group_arn = {_resolve_to_expr(lb0.get('TargetGroupArn'), **ctx)}")
                    main_parts.append(f"    container_name   = {json.dumps(lb0.get('ContainerName', 'app'))}")
                    main_parts.append(
                        f"    container_port   = {_resolve_to_expr(lb0.get('ContainerPort'), **ctx)}"
                    )
                    main_parts.append("  }")
            dc = props.get("DeploymentConfiguration") or {}
            if isinstance(dc, dict):
                main_parts.append("  deployment_maximum_percent         = "
                    f"{dc.get('MaximumPercent', 200)}"
                )
                main_parts.append("  deployment_minimum_healthy_percent = "
                    f"{dc.get('MinimumHealthyPercent', 100)}"
                )
            main_parts.append("}")
            main_parts.append("")
            supported.append(f"{lid} ({cfn_type})")
            continue

        if rt:
            main_parts.append(_unsupported_resource_block(lid, str(cfn_type), props))
            skipped.append(f"{lid} ({cfn_type})")
        else:
            main_parts.append(_unsupported_resource_block(lid, str(cfn_type), props))
            skipped.append(f"{lid} ({cfn_type})")

    main_tf = "\n".join(main_parts)

    # outputs.tf
    outputs_parts: list[str] = ["# Generated from CloudFormation Outputs.\n"]
    outs = template.get("Outputs") or {}
    if isinstance(outs, dict):
        for oid, ospec in outs.items():
            if not isinstance(ospec, dict):
                continue
            on = _snake(oid)
            val = ospec.get("Value")
            desc = (ospec.get("Description") or "").replace('"', "'")
            expr = _resolve_to_expr(val, **ctx) if val is not None else '"TODO"'
            outputs_parts.append(f'output "{on}" {{')
            if desc:
                outputs_parts.append(f'  description = "{desc}"')
            outputs_parts.append(f"  value       = {expr}")
            outputs_parts.append("}")
            outputs_parts.append("")
    outputs_tf = "\n".join(outputs_parts)

    vars_tf = _emit_variables_tf(parameters, stack_var)
    if "variable \"aws_region\"" not in vars_tf:
        pass  # aws_region is only in main for this generator; add to variables file
    vars_tf = (
        variables_aws_region()
        + vars_tf
    )

    rel_base = output_relative_directory.strip().rstrip("/")
    written: list[str] = []

    async def w(rel: str, content: str) -> dict[str, Any]:
        return await write_local_workspace_file(rel, content, create_directories=True)

    r1 = await w(f"{rel_base}/main.tf", main_tf)
    if not r1.get("ok"):
        return {"ok": False, "error": r1.get("error"), "step": "main.tf"}
    written.append(r1["path"])

    r2 = await w(f"{rel_base}/variables.tf", vars_tf)
    if not r2.get("ok"):
        return {"ok": False, "error": r2.get("error"), "step": "variables.tf"}
    written.append(r2["path"])

    r3 = await w(f"{rel_base}/outputs.tf", outputs_tf)
    if not r3.get("ok"):
        return {"ok": False, "error": r3.get("error"), "step": "outputs.tf"}
    written.append(r3["path"])

    r_readme = await w(
        f"{rel_base}/README.md",
        _conversion_readme_md(rel_base, str(src.resolve())),
    )
    if not r_readme.get("ok"):
        return {"ok": False, "error": r_readme.get("error"), "step": "README.md"}
    written.append(r_readme["path"])

    pat_hints = _pattern_catalog_hints(logical_to_cfn_type)

    if write_pattern_catalog_readme:
        readme = _pattern_catalog_readme(pat_hints, rel_base)
        r4 = await w(f"{rel_base}/PATTERN_CATALOG.md", readme)
        if r4.get("ok"):
            written.append(r4["path"])

    return {
        "ok": True,
        "source_template": str(src.resolve()),
        "output_directory_relative": rel_base,
        "files_written": written,
        "resources_supported": supported,
        "resources_skipped_or_todo": skipped,
        "pattern_catalog_hints": pat_hints,
        "note": (
            "Terraform is generated heuristically. Run `terraform fmt` and validate. "
            "Use Pattern Catalogue MCP tools in the agent to swap in approved module sources."
        ),
    }


def variables_aws_region() -> str:
    return '''variable "aws_region" {
  type        = string
  description = "AWS region (provider)."
  default     = "us-east-1"
}

'''


def _pattern_catalog_hints(logical_to_cfn_type: dict[str, str]) -> list[dict[str, str]]:
    hints: list[dict[str, str]] = []
    types_seen = set(logical_to_cfn_type.values())
    if "AWS::ECS::Cluster" in types_seen or "AWS::ECS::Service" in types_seen:
        hints.append(
            {
                "topic": "ECS Fargate",
                "suggestion": (
                    "Call Pattern Catalogue MCP tools (e.g. search/list modules for ECS, Fargate, "
                    "task definition) and replace aws_ecs_* resources with the approved module blocks "
                    "and inputs from your catalog."
                ),
            }
        )
    if "AWS::ElasticLoadBalancingV2::LoadBalancer" in types_seen:
        hints.append(
            {
                "topic": "Application Load Balancer",
                "suggestion": (
                    "Discover internal ALB / load-balancer modules via Pattern Catalogue; map "
                    "subnets, security groups, and listeners to module variables."
                ),
            }
        )
    if "AWS::IAM::Role" in types_seen:
        hints.append(
            {
                "topic": "IAM",
                "suggestion": (
                    "Align task execution and task roles with catalog IAM modules or policies; "
                    "avoid copying admin-equivalent policies from samples."
                ),
            }
        )
    if not hints:
        hints.append(
            {
                "topic": "General",
                "suggestion": (
                    "Use Pattern Catalogue MCP to find Terraform modules matching each AWS "
                    "resource type in this template."
                ),
            }
        )
    return hints


def _conversion_readme_md(rel_dir: str, template_path: str) -> str:
    return f"""# Terraform stack

Converted from CloudFormation template:

`{template_path}`

## Layout

| File | Purpose |
|------|---------|
| `main.tf` | Provider and resources |
| `variables.tf` | Input variables (from Parameters) |
| `outputs.tf` | Outputs (from CloudFormation Outputs) |
| `PATTERN_CATALOG.md` | Pattern Catalogue alignment and next steps |

## Next steps

1. Run `terraform fmt` and `terraform validate`.
2. Use **Pattern Catalogue** MCP tools in this agent to replace raw `aws_*` resources with approved internal modules where required.

Output folder (relative to agent output root): `{rel_dir}/`
"""


def _pattern_catalog_readme(hints: list[dict[str, str]], rel_dir: str) -> str:
    lines = [
        "# Pattern Catalogue alignment",
        "",
        "This directory was produced by `convert_cloudformation_template_to_terraform`.",
        "Raw `aws_*` resources mirror the CloudFormation template; they are **not** necessarily",
        "the approved internal modules for your organization.",
        "",
        "## Next steps (agent workflow)",
        "",
        "1. Use **Pattern Catalogue** MCP tools exposed in this agent (same session) to search",
        "   for modules covering ECS, ALB, IAM, and logging.",
        "2. Replace resource blocks with `module` calls using the **sources and variable names**",
        "   returned by those tools.",
        "3. Run `terraform fmt` and `terraform validate` locally.",
        "4. Optionally run `scan_local_terraform_code` on this folder after Wiz CLI authentication.",
        "",
        "## Hints for this template",
        "",
    ]
    for h in hints:
        lines.append(f"- **{h['topic']}**: {h['suggestion']}")
    lines.extend(
        [
            "",
            f"Output folder (relative to agent output root): `{rel_dir}/`",
            "",
        ]
    )
    return "\n".join(lines) + "\n"
