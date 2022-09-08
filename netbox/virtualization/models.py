from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse

from dcim.models import BaseInterface, Device
from extras.models import ConfigContextModel
from extras.querysets import ConfigContextModelQuerySet
from netbox.config import get_config
from netbox.models import OrganizationalModel, NetBoxModel
from utilities.fields import NaturalOrderingField
from utilities.ordering import naturalize_interface
from utilities.query_functions import CollateAsChar
from .choices import *

__all__ = (
    'Cluster',
    'ClusterGroup',
    'ClusterType',
    'VirtualMachine',
    'VMInterface',
)


#
# Cluster types
#

class ClusterType(OrganizationalModel):
    """
    A type of Cluster.
    """
    name = models.CharField(
        max_length=100,
        unique=True
    )
    slug = models.SlugField(
        max_length=100,
        unique=True
    )
    description = models.CharField(
        max_length=200,
        blank=True
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('virtualization:clustertype', args=[self.pk])


#
# Cluster groups
#

class ClusterGroup(OrganizationalModel):
    """
    An organizational group of Clusters.
    """
    name = models.CharField(
        max_length=100,
        unique=True
    )
    slug = models.SlugField(
        max_length=100,
        unique=True
    )
    description = models.CharField(
        max_length=200,
        blank=True
    )

    # Generic relations
    vlan_groups = GenericRelation(
        to='ipam.VLANGroup',
        content_type_field='scope_type',
        object_id_field='scope_id',
        related_query_name='cluster_group'
    )
    contacts = GenericRelation(
        to='tenancy.ContactAssignment'
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('virtualization:clustergroup', args=[self.pk])


#
# Clusters
#

class Cluster(NetBoxModel):
    """
    A cluster of VirtualMachines. Each Cluster may optionally be associated with one or more Devices.
    """
    name = models.CharField(
        max_length=100
    )
    type = models.ForeignKey(
        to=ClusterType,
        on_delete=models.PROTECT,
        related_name='clusters'
    )
    group = models.ForeignKey(
        to=ClusterGroup,
        on_delete=models.PROTECT,
        related_name='clusters',
        blank=True,
        null=True
    )
    status = models.CharField(
        max_length=50,
        choices=ClusterStatusChoices,
        default=ClusterStatusChoices.STATUS_ACTIVE
    )
    tenant = models.ForeignKey(
        to='tenancy.Tenant',
        on_delete=models.PROTECT,
        related_name='clusters',
        blank=True,
        null=True
    )
    site = models.ForeignKey(
        to='dcim.Site',
        on_delete=models.PROTECT,
        related_name='clusters',
        blank=True,
        null=True
    )
    comments = models.TextField(
        blank=True
    )

    # Generic relations
    vlan_groups = GenericRelation(
        to='ipam.VLANGroup',
        content_type_field='scope_type',
        object_id_field='scope_id',
        related_query_name='cluster'
    )
    contacts = GenericRelation(
        to='tenancy.ContactAssignment'
    )

    clone_fields = (
        'type', 'group', 'status', 'tenant', 'site',
    )

    class Meta:
        ordering = ['name']
        unique_together = (
            ('group', 'name'),
            ('site', 'name'),
        )

    def __str__(self):
        return self.name

    @classmethod
    def get_prerequisite_models(cls):
        return [ClusterType, ]

    def get_absolute_url(self):
        return reverse('virtualization:cluster', args=[self.pk])

    def get_status_color(self):
        return ClusterStatusChoices.colors.get(self.status)

    def clean(self):
        super().clean()

        # If the Cluster is assigned to a Site, verify that all host Devices belong to that Site.
        if self.pk and self.site:
            nonsite_devices = Device.objects.filter(cluster=self).exclude(site=self.site).count()
            if nonsite_devices:
                raise ValidationError({
                    'site': "{} devices are assigned as hosts for this cluster but are not in site {}".format(
                        nonsite_devices, self.site
                    )
                })


#
# Virtual machines
#

class VirtualMachine(NetBoxModel, ConfigContextModel):
    """
    A virtual machine which runs inside a Cluster.
    """
    site = models.ForeignKey(
        to='dcim.Site',
        on_delete=models.PROTECT,
        related_name='virtual_machines',
        blank=True,
        null=True
    )
    cluster = models.ForeignKey(
        to='virtualization.Cluster',
        on_delete=models.PROTECT,
        related_name='virtual_machines',
        blank=True,
        null=True
    )
    device = models.ForeignKey(
        to='dcim.Device',
        on_delete=models.PROTECT,
        related_name='virtual_machines',
        blank=True,
        null=True
    )
    tenant = models.ForeignKey(
        to='tenancy.Tenant',
        on_delete=models.PROTECT,
        related_name='virtual_machines',
        blank=True,
        null=True
    )
    platform = models.ForeignKey(
        to='dcim.Platform',
        on_delete=models.SET_NULL,
        related_name='virtual_machines',
        blank=True,
        null=True
    )
    name = models.CharField(
        max_length=64
    )
    _name = NaturalOrderingField(
        target_field='name',
        max_length=100,
        blank=True
    )
    status = models.CharField(
        max_length=50,
        choices=VirtualMachineStatusChoices,
        default=VirtualMachineStatusChoices.STATUS_ACTIVE,
        verbose_name='Status'
    )
    role = models.ForeignKey(
        to='dcim.DeviceRole',
        on_delete=models.PROTECT,
        related_name='virtual_machines',
        limit_choices_to={'vm_role': True},
        blank=True,
        null=True
    )
    primary_ip4 = models.OneToOneField(
        to='ipam.IPAddress',
        on_delete=models.SET_NULL,
        related_name='+',
        blank=True,
        null=True,
        verbose_name='Primary IPv4'
    )
    primary_ip6 = models.OneToOneField(
        to='ipam.IPAddress',
        on_delete=models.SET_NULL,
        related_name='+',
        blank=True,
        null=True,
        verbose_name='Primary IPv6'
    )
    vcpus = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name='vCPUs',
        validators=(
            MinValueValidator(0.01),
        )
    )
    memory = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name='Memory (MB)'
    )
    disk = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name='Disk (GB)'
    )
    comments = models.TextField(
        blank=True
    )

    # Generic relation
    contacts = GenericRelation(
        to='tenancy.ContactAssignment'
    )

    objects = ConfigContextModelQuerySet.as_manager()

    clone_fields = (
        'site', 'cluster', 'device', 'tenant', 'platform', 'status', 'role', 'vcpus', 'memory', 'disk',
    )

    class Meta:
        ordering = ('_name', 'pk')  # Name may be non-unique
        unique_together = [
            ['cluster', 'tenant', 'name']
        ]

    def __str__(self):
        return self.name

    @classmethod
    def get_prerequisite_models(cls):
        return [Cluster, ]

    def get_absolute_url(self):
        return reverse('virtualization:virtualmachine', args=[self.pk])

    def validate_unique(self, exclude=None):

        # Check for a duplicate name on a VM assigned to the same Cluster and no Tenant. This is necessary
        # because Django does not consider two NULL fields to be equal, and thus will not trigger a violation
        # of the uniqueness constraint without manual intervention.
        if self.tenant is None and VirtualMachine.objects.exclude(pk=self.pk).filter(
                name=self.name, cluster=self.cluster, tenant__isnull=True
        ):
            raise ValidationError({
                'name': 'A virtual machine with this name already exists in the assigned cluster.'
            })

        super().validate_unique(exclude)

    def clean(self):
        super().clean()

        # Must be assigned to a site and/or cluster
        if not self.site and not self.cluster:
            raise ValidationError({
                'cluster': f'A virtual machine must be assigned to a site and/or cluster.'
            })

        # Validate site for cluster & device
        if self.cluster and self.cluster.site != self.site:
            raise ValidationError({
                'cluster': f'The selected cluster ({self.cluster} is not assigned to this site ({self.site}).'
            })
        if self.device and self.device.site != self.site:
            raise ValidationError({
                'device': f'The selected device ({self.device} is not assigned to this site ({self.site}).'
            })

        # Validate assigned cluster device
        if self.device and not self.cluster:
            raise ValidationError({
                'device': f'Must specify a cluster when assigning a host device.'
            })
        if self.device and self.device not in self.cluster.devices.all():
            raise ValidationError({
                'device': f'The selected device ({self.device} is not assigned to this cluster ({self.cluster}).'
            })

        # Validate primary IP addresses
        interfaces = self.interfaces.all()
        for family in (4, 6):
            field = f'primary_ip{family}'
            ip = getattr(self, field)
            if ip is not None:
                if ip.address.version != family:
                    raise ValidationError({
                        field: f"Must be an IPv{family} address. ({ip} is an IPv{ip.address.version} address.)",
                    })
                if ip.assigned_object in interfaces:
                    pass
                elif ip.nat_inside is not None and ip.nat_inside.assigned_object in interfaces:
                    pass
                else:
                    raise ValidationError({
                        field: f"The specified IP address ({ip}) is not assigned to this VM.",
                    })

    def get_status_color(self):
        return VirtualMachineStatusChoices.colors.get(self.status)

    @property
    def primary_ip(self):
        if get_config().PREFER_IPV4 and self.primary_ip4:
            return self.primary_ip4
        elif self.primary_ip6:
            return self.primary_ip6
        elif self.primary_ip4:
            return self.primary_ip4
        else:
            return None


#
# Interfaces
#

class VMInterface(NetBoxModel, BaseInterface):
    virtual_machine = models.ForeignKey(
        to='virtualization.VirtualMachine',
        on_delete=models.CASCADE,
        related_name='interfaces'
    )
    name = models.CharField(
        max_length=64
    )
    _name = NaturalOrderingField(
        target_field='name',
        naturalize_function=naturalize_interface,
        max_length=100,
        blank=True
    )
    description = models.CharField(
        max_length=200,
        blank=True
    )
    untagged_vlan = models.ForeignKey(
        to='ipam.VLAN',
        on_delete=models.SET_NULL,
        related_name='vminterfaces_as_untagged',
        null=True,
        blank=True,
        verbose_name='Untagged VLAN'
    )
    tagged_vlans = models.ManyToManyField(
        to='ipam.VLAN',
        related_name='vminterfaces_as_tagged',
        blank=True,
        verbose_name='Tagged VLANs'
    )
    ip_addresses = GenericRelation(
        to='ipam.IPAddress',
        content_type_field='assigned_object_type',
        object_id_field='assigned_object_id',
        related_query_name='vminterface'
    )
    vrf = models.ForeignKey(
        to='ipam.VRF',
        on_delete=models.SET_NULL,
        related_name='vminterfaces',
        null=True,
        blank=True,
        verbose_name='VRF'
    )
    fhrp_group_assignments = GenericRelation(
        to='ipam.FHRPGroupAssignment',
        content_type_field='interface_type',
        object_id_field='interface_id',
        related_query_name='+'
    )
    l2vpn_terminations = GenericRelation(
        to='ipam.L2VPNTermination',
        content_type_field='assigned_object_type',
        object_id_field='assigned_object_id',
        related_query_name='vminterface',
    )

    class Meta:
        verbose_name = 'interface'
        ordering = ('virtual_machine', CollateAsChar('_name'))
        unique_together = ('virtual_machine', 'name')

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('virtualization:vminterface', kwargs={'pk': self.pk})

    def clean(self):
        super().clean()

        # Parent validation

        # An interface cannot be its own parent
        if self.pk and self.parent_id == self.pk:
            raise ValidationError({'parent': "An interface cannot be its own parent."})

        # An interface's parent must belong to the same virtual machine
        if self.parent and self.parent.virtual_machine != self.virtual_machine:
            raise ValidationError({
                'parent': f"The selected parent interface ({self.parent}) belongs to a different virtual machine "
                          f"({self.parent.virtual_machine})."
            })

        # Bridge validation

        # An interface cannot be bridged to itself
        if self.pk and self.bridge_id == self.pk:
            raise ValidationError({'bridge': "An interface cannot be bridged to itself."})

        # A bridged interface belong to the same virtual machine
        if self.bridge and self.bridge.virtual_machine != self.virtual_machine:
            raise ValidationError({
                'bridge': f"The selected bridge interface ({self.bridge}) belongs to a different virtual machine "
                          f"({self.bridge.virtual_machine})."
            })

        # VLAN validation

        # Validate untagged VLAN
        if self.untagged_vlan and self.untagged_vlan.site not in [self.virtual_machine.site, None]:
            raise ValidationError({
                'untagged_vlan': f"The untagged VLAN ({self.untagged_vlan}) must belong to the same site as the "
                                 f"interface's parent virtual machine, or it must be global."
            })

    def to_objectchange(self, action):
        objectchange = super().to_objectchange(action)
        objectchange.related_object = self.virtual_machine
        return objectchange

    @property
    def parent_object(self):
        return self.virtual_machine

    @property
    def l2vpn_termination(self):
        return self.l2vpn_terminations.first()
