"""Library model objects."""
from odoo import api, fields, models


class LibraryType:
    """Different types of libraries."""

    PUBLIC = "PUBLIC"
    ACADEMIC = "ACADEMIC"
    SCHOOL = "SCHOOL"
    INDUSTRY = "INDUSTRY"

    OPTIONS = [PUBLIC, ACADEMIC, SCHOOL, INDUSTRY]
    SELECTION = [
        ("Public", PUBLIC),
        ("Academic", ACADEMIC),
        ("School", SCHOOL),
        ("Industry", INDUSTRY),
    ]


class Library(models.Model):
    """A library."""

    _name = "library"
    _description = "A physical library."
    _inherit = "ownerless.abstract.base"

    user = fields.Many2one(
        "res.users",
        ondelete="restrict",
        domain=lambda self: self._current_user_domain(),
    )
    name = fields.Char(
        help="The name of the library.",
        required=True,
        copy=False,
        string="Library Name",
    )
    address = fields.Char(
        help="Physical address of the library",
        required=True,
        copy=False,
        string="Library Address",
    )
    library_type = fields.Selection(
        selection=LibraryType.SELECTION,
        string="Type",
        help="The type of a library",
        required=True,
    )
    phone_number = fields.Char(
        help="The primary phone number of the library",
        required=True,
        copy=False,
        string="Library Phone Number",
    )
    email = fields.Char(
        help="The primary email address of the library",
        copy=False,
        string="Library Email",
    )  # Todo: Validate phone number and email
    borrowing_settings = fields.One2many("borrowing.settings", "library")
    fine_settings = fields.One2many("fine.settings", "library")

    @api.depends("name")
    def name_get(self):
        """Display name of library model."""
        display = []
        for record in self:
            display.append((record.id, record.name))
        return display

    def _current_user_domain(self):
        """Current user search domain."""
        user_id = self.env.user.id
        domain = [("id", "=", user_id)]
        return domain


class DurationType:
    """Calender duration type."""

    DAYS = "Days"
    WEEKS = "Weeks"
    MONTHS = "Months"
    YEARS = "Years"

    OPTIONS = [DAYS, WEEKS, MONTHS, YEARS]
    SELECTION = [
        ("Days", DAYS),
        ("Weeks", WEEKS),
        ("Months", MONTHS),
        ("Years", YEARS),
    ]


class BorrowingSettings(models.Model):
    """Library custom borrowing settings."""

    _name = "borrowing.settings"
    _description = "Custom metadata about a library."
    _inherit = "abstract.base"

    duration = fields.Integer(
        required=True, help="The default duration a book can be borrowed."
    )
    duration_type = fields.Selection(
        selection=DurationType.SELECTION,
        required=True,
        help="Calender bands for duration.",
    )

    @api.constrains("library")
    def validate_only_one_setting(self):
        """Ensure there is only one borrowing setting."""
        pass


class FineSettings(models.Model):
    """Library custom fine settings."""

    _name = "fine.settings"
    _description = "Custom metadata about a library's fine details."
    _inherit = "abstract.base"

    duration_type = fields.Selection(
        selection=DurationType.SELECTION,
        required=True,
        help="Calender bands for duration.",
    )
    amount = fields.Float(required=True, copy=False)

    @api.constrains("library")
    def validate_only_one_setting(self):
        """Ensure there is only one fines setting."""
        pass
