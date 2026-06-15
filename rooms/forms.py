from django import forms
from .models import Room


class RoomCreateForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ('title', 'description', 'room_type', 'password', 'max_participants',
                  'enable_waiting_room', 'mute_on_entry', 'allow_screen_share', 'allow_chat',
                  'scheduled_start', 'scheduled_end')
        widgets = {
            'scheduled_start': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'scheduled_end': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'lsf-checkbox'})
            else:
                field.widget.attrs.update({'class': 'lsf-input'})
