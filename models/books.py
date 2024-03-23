"""Book business object."""
import datetime
import time

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from .base import AbstractBase


class BookFormat:
    """Class to store the various types of book formats."""

    HARD_COVER = "Hard Cover"
    PAPER_BACK = "Paper Back"
    AUDIO_BOOK = "Audio Book"
    EBOOK = "Ebook"
    NEWSPAPER = "Newspaper"
    MAGAZINE = "Magazine"
    JOURNAL = "Journal"

    OPTIONS = [
        HARD_COVER,
        PAPER_BACK,
        AUDIO_BOOK,
        EBOOK,
        NEWSPAPER,
        MAGAZINE,
        JOURNAL,
    ]
    SELECTION = [
        ("Hard Cover", HARD_COVER),
        ("Paper Back", PAPER_BACK),
        ("Audio Book", AUDIO_BOOK),
        ("EBook", EBOOK),
        ("Newspaper", NEWSPAPER),
        ("Magazine", MAGAZINE),
        ("Journal", JOURNAL),
    ]


class Author(models.Model):
    """Author of a book(s)."""

    _name = "author"
    _description = "An author of a book in a library."
    _inherit = "abstract.base"

    name = fields.Char(required=True, copy=False, help="Name of an author.")

    @api.depends("name")
    def name_get(self):
        """Display name of author model."""
        display = []
        for record in self:
            display.append((record.id, record.name))
        return display


class Book(models.Model):
    """Book object model."""

    _name = "book"
    _description = "A book in a library."
    _inherit = "abstract.base"

    name = fields.Char(
        string="Name",
        help="The title/name of the book to be added",
        required=True,
        copy=False,
    )
    subject = fields.Char(
        help="The subject covered by the book.", required=True, copy=False
    )
    publisher = fields.Char(
        help="The publisher of the book", required=True, copy=False
    )
    language = fields.Char(
        help="The language the book is written in", default="en"
    )
    pages = fields.Integer(
        help="The number of readable pages a book has.",
        required=True,
        copy=False,
    )
    format = fields.Selection(
        selection=BookFormat.SELECTION, default=BookFormat.HARD_COVER
    )
    description = fields.Text(
        copy=False, help="A general description of the book"
    )
    author = fields.Many2one(
        "author",
        required=True,
        ondelete="restrict",
        help=(
            "A foreign key to an author who wrote the book. "
            "The author is stored in a different model."
        ),
    )
    book_items = fields.One2many("book.item", "book", string="Book Items")

    @api.depends("title", "author")
    def name_get(self):
        """Display name of book model."""
        display = []
        for record in self:
            name = f"{record.name} : {record.author.name}"
            display.append((record.id, name))
        return display


class BookStatus:
    """Class to store the various statuses a book item has."""

    AVAILABLE = "Available"
    RESERVED = "Reserved"
    BORROWED = "Borrowed"
    LOST = "Lost"

    OPTIONS = [AVAILABLE, RESERVED, BORROWED, LOST]
    SELECTION = [
        ("Available", AVAILABLE),
        ("Reserved", RESERVED),
        ("Borrowed", BORROWED),
        ("Lost", LOST),
    ]


class BookItem(models.Model):
    """A single book."""

    _name = "book.item"
    _description = "A single book item in a library."
    _inherit = "abstract.base"

    book = fields.Many2one("book", required=True, ondelete="restrict")
    barcode = fields.Char(
        help="A unique bar code to identify a unique book",
        copy=False,
        default=lambda self: self._barcode(),
        readonly=True,
    )
    status = fields.Selection(
        selection=BookStatus.SELECTION, default=BookStatus.AVAILABLE
    )
    issued_to = fields.One2many(
        "issued.book.item",
        "book_item",
        help="Historical of members who have been issued the book.",
        readonly=True,
    )
    borrowed_by = fields.Many2one(
        "member", ondelete="restrict", string="Member"
    )
    reserved_by = fields.Many2one(
        "member", ondelete="restrict", string="Member"
    )
    reservations = fields.One2many("book.item.reservation", "book_item")
    fines = fields.One2many("fine", "book_item")

    def _barcode(self):
        """System generated barcode."""
        timestamp = str(time.time())[-6:]
        return f"BAR-{timestamp}"

    def _due_date(self):
        """Calculate the due date of a book item."""
        library = AbstractBase.current_library(self)
        library_borrowing_settings = library.borrowing_settings[0]
        if not library_borrowing_settings:
            raise UserError(
                "Session library has no active borrowing settings."
            )

        duration = library_borrowing_settings.duration
        borrowed_date = datetime.datetime.now()
        due_date = None
        if library_borrowing_settings.duration_type == "Days":
            due_date = borrowed_date + datetime.timedelta(days=duration)

        elif library_borrowing_settings.duration_type == "Weeks":
            due_date = borrowed_date + datetime.timedelta(weeks=duration)

        elif library_borrowing_settings.duration_type == "Months":
            due_date = borrowed_date + datetime.timedelta(months=duration)

        elif library_borrowing_settings.duration_type == "Years":
            due_date = borrowed_date + datetime.timedelta(years=duration)

        else:
            raise UserError("Calendar band not implemented.")

        return due_date

    @api.depends("barcode")
    def name_get(self):
        """Display name of book item model."""
        display = []
        for record in self:
            display.append((record.id, record.barcode))
        return display

    @api.constrains("status", "borrowed_by")
    def validate_borrowed_by_status(self):
        """Ensure borrowed_by is supplied when borrowing a book."""
        if self.status == BookStatus.BORROWED and not self.borrowed_by:
            raise ValidationError(
                "Provide a member before borrowing a book item."
            )

    @api.constrains("status", "reserved_by")
    def validate_reserved_by_status(self):
        """Ensure reserved_by is supplied when reserving a book."""
        if self.status == BookStatus.RESERVED and not self.reserved_by:
            raise ValidationError(
                "Provide a member before reserving a book item."
            )

    def update_borrowed_fields(self, record):
        """Update borrowed fields metadata."""
        issued_book = self.env["issued.book.item"].search(
            [
                ("member", "=", record.borrowed_by.id),
                ("book_item", "=", record.id),
                ("returned_date", "=", False),
            ]
        )
        if len(issued_book) != 0:
            raise ValidationError(
                "This book item has already been borrowed by this member."
            )

        record.status = BookStatus.BORROWED
        record.reserved_by = False
        borrowed_date = datetime.datetime.now()
        due_date = self._due_date()
        issued_book_payload = {
            "member": record.borrowed_by.id,
            "book_item": record.id,
            "borrowed_date": borrowed_date,
            "due_date": due_date,
        }
        self.env["issued.book.item"].create(issued_book_payload)

    def action_borrow_book(self):
        """Action to borrow a book."""
        for record in self:
            if record.status == BookStatus.AVAILABLE:
                self.update_borrowed_fields(record)

            elif record.status == BookStatus.RESERVED:
                reservation = self.env["book.item.reservation"].search(
                    [
                        ("book_item", "=", self.id),
                        ("member", "=", self.borrowed_by.id),
                        ("status", "=", ReservationStatus.WAITING),
                    ]
                )
                if not reservation:
                    raise ValidationError(
                        "The member does not have a waiting reservation to this book item."
                    )

                self.update_borrowed_fields(record)
                update_payload = {"status": ReservationStatus.COMPLETED}
                reservation.write(update_payload)

            elif record.status == BookStatus.BORROWED:
                raise ValidationError(
                    "The book has already been borrowed by another member."
                )

            elif record.status == BookStatus.LOST:
                raise ValidationError("The book is lost to the library.")

            else:
                raise ValidationError("Status not implemented.")

        return True

    def action_return_book(self):
        """Action to return a borrowed book."""
        for record in self:
            if record.status != BookStatus.BORROWED:
                raise ValidationError("You can only return a borrowed book.")

            returned_date = datetime.datetime.now()
            issued_book_item = self.env["issued.book.item"].search(
                [
                    ("member", "=", record.borrowed_by.id),
                    ("book_item", "=", record.id),
                    ("returned_date", "=", False),
                ]
            )
            issued_book_item.write({"returned_date": returned_date})
            record.status = BookStatus.AVAILABLE

            due_date = issued_book_item.due_date
            if returned_date > due_date:
                fine_payload = {
                    "member": record.borrowed_by.id,
                    "book_item": record.id,
                    "due_date": due_date,
                    "returned_date": returned_date,
                }
                self.env["fine"].create(fine_payload)

            record.borrowed_by = False

        return True

    def action_report_lost_book(self):
        """Report a book item as lost."""
        for record in self:
            record.status = BookStatus.LOST

        return True

    def action_reserve_book(self):
        """Action to create a book reservation."""
        for record in self:
            record.status = BookStatus.RESERVED
            reservation_payload = {
                "book_item": record.id,
                "member": record.reserved_by.id,
            }
            self.env["book.item.reservation"].create(reservation_payload)

        return True


class IssuedBookItem(models.Model):
    """Book item issued to a member."""

    _name = "issued.book.item"
    _description = "Book item(s) issued to a library member"
    _inherit = "abstract.base"

    member = fields.Many2one(
        "member", required=True, ondelete="restrict", readonly=True
    )
    book_item = fields.Many2one(
        "book.item", required=True, ondelete="restrict", readonly=True
    )
    borrowed_date = fields.Datetime(
        help="The borrowed date of the issued book item.",
        copy=False,
        readonly=True,
    )
    due_date = fields.Datetime(
        help="The return date of the issued book item.",
        copy=False,
        readonly=True,
    )
    returned_date = fields.Datetime(
        help="The actual return date of the issued book item.",
        copy=False,
    )

    @api.depends("book_item")
    def name_get(self):
        """Display name of book item model."""
        display = []
        for record in self:
            name = f"{record.book_item.book.title}"
            display.append((record.id, name))
        return display


class ReservationStatus:
    """Class to store the various statuses of a reservation."""

    WAITING = "Waiting"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"

    OPTIONS = [WAITING, COMPLETED, CANCELLED]
    SELECTION = [
        ("Waiting", WAITING),
        ("Completed", COMPLETED),
        ("Cancelled", CANCELLED),
    ]


class BookItemReservation(models.Model):
    """Book item reservation information."""

    _name = "book.item.reservation"
    _description = "A reservation made on a book item."
    _inherit = "abstract.base"

    book_item = fields.Many2one(
        "book.item", required=True, ondelete="restrict"
    )
    member = fields.Many2one("member", required=True, ondelete="restrict")
    reserved_on = fields.Datetime(
        default=lambda self: fields.Datetime.now(),
        help="Date when a reservation is made.",
    )
    status = fields.Selection(
        selection=ReservationStatus.SELECTION,
        default=ReservationStatus.WAITING,
        help="Status of a book item reservation.",
    )

    @api.constrains("book_item")
    def validate_reserve_available_book_items(self):
        for record in self:
            if record.book_item.status == BookStatus.LOST:
                raise ValidationError(
                    "You can't reserve a book lost to the library."
                )

    @api.constrains("member", "book_item")
    def validate_member_item_reservation(self):
        """A member can only reserve a book once."""
        for record in self:
            reservation = self.env["book.item.reservation"].search(
                [
                    ("book_item", "=", record.book_item.id),
                    ("member", "=", record.member.id),
                    ("status", "=", ReservationStatus.WAITING),
                ]
            )
            if len(reservation) > 1:
                raise ValidationError(
                    "A member can only have one reservation for this book item."
                )

    @api.constrains("member", "book_item")
    def validate_reserving_a_self_borrowed_book(self):
        """A member should not reserve a book they have borrowed."""
        for record in self:
            if (
                record.book_item.status == BookStatus.BORROWED
                and record.book_item.borrowed_by == record.member
            ):
                raise ValidationError(
                    "You can not reserve a book you have already borrowed. Return it first."
                )

    @api.depends("book_item")
    def name_get(self):
        """Display name of book item reservation model."""
        display = []
        for record in self:
            name = f"Reservation for {record.book_item.book.title}"
            display.append((record.id, name))
        return display

    def action_cancel_reservation(self):
        """Action to cancel a reservation."""
        for record in self:
            record.status = ReservationStatus.CANCELLED

        return True


class Fine(models.Model):
    """Accrued fines on late/lost book returns."""

    _name = "fine"
    _description = "Fine applied to a particular late book item."
    _inherit = "abstract.base"

    member = fields.Many2one("member", required=True, ondelete="restrict")
    book_item = fields.Many2one(
        "book.item", required=True, ondelete="restrict"
    )
    amount = fields.Float(
        copy=False, default=lambda self: self._compute_fine()
    )
    due_date = fields.Datetime(
        help="The return date of the issued book item.",
        copy=False,
    )
    returned_date = fields.Datetime(
        help="The actual return date of the issued book item.",
        copy=False,
    )

    def _compute_fine(self):
        """Compute fines acquired."""
        library = AbstractBase.current_library(self)
        library_fine_settings = library.fine_settings[0]
        if not library_fine_settings:
            raise UserError("Session library has no active fines settings.")

        delta = None
        if library_fine_settings.duration_type == "Days":
            delta = self.returned_date - self.due_date

        elif library_fine_settings.duration_type == "Weeks":
            delta = self.returned_date - self.due_date

        elif library_fine_settings.duration_type == "Months":
            delta = self.returned_date - self.due_date

        elif library_fine_settings.duration_type == "Years":
            delta = self.returned_date - self.due_date

        else:
            raise UserError("Calendar band not implemented.")

        return delta * library_fine_settings.amount
