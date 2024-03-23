"""Library member business objects."""
from odoo import api, fields, models


class Member(models.Model):
    """A library member."""

    _name = "member"
    _description = "A member of a library."
    _inherit = "abstract.base"

    name = fields.Char(required=True, copy=False)
    registered_on = fields.Datetime(default=lambda self: fields.Datetime.now())
    removed_on = fields.Datetime()
    phone_number = fields.Char(
        help="The primary phone number of the member",
        required=True,
        copy=False,
    )
    email = fields.Char(
        help="The primary email address of the member",
        copy=False,
    )
    issued_book_items = fields.One2many(
        "issued.book.item", "member", string="Issued Book Items"
    )

    @api.depends("name")
    def name_get(self):
        """Display name of member model."""
        display = []
        for record in self:
            display.append((record.id, record.name))
        return display
