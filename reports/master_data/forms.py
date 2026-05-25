from django import forms

from reports.master_data.models import (
    Project,
    MasterCode,
    EquipmentMaster,
    LookupItem,
)


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = "__all__"


class MasterCodeForm(forms.ModelForm):
    class Meta:
        model = MasterCode
        fields = "__all__"


class EquipmentMasterForm(forms.ModelForm):
    class Meta:
        model = EquipmentMaster
        fields = "__all__"


class LookupItemForm(forms.ModelForm):
    class Meta:
        model = LookupItem
        fields = "__all__"