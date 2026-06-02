from django import forms


class StyledFormMixin:
    file_widgets = (forms.ClearableFileInput,)
    checkbox_widgets = (forms.CheckboxInput, forms.CheckboxSelectMultiple, forms.RadioSelect)
    select_widgets = (forms.Select, forms.SelectMultiple)

    def apply_bootstrap_styles(self) -> None:
        for field in self.fields.values():
            widget = field.widget
            existing = widget.attrs.get("class", "")
            if isinstance(widget, self.checkbox_widgets):
                css_class = "form-check-input"
            elif isinstance(widget, self.file_widgets):
                css_class = "form-control"
            elif isinstance(widget, self.select_widgets):
                css_class = "form-select"
            else:
                css_class = "form-control"

            widget.attrs["class"] = " ".join(part for part in [existing, css_class] if part).strip()

            if isinstance(widget, forms.DateInput):
                widget.attrs.setdefault("type", "date")
            if isinstance(widget, forms.DateTimeInput):
                widget.attrs.setdefault("type", "datetime-local")
            if isinstance(widget, forms.Textarea):
                widget.attrs.setdefault("rows", 3)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_styles()
