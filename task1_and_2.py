from __future__ import annotations
from collections import UserDict
from datetime import datetime, date, timedelta


def parse_input(user_input: str):
    parts = user_input.strip().split()
    if not parts:
        return "", []
    return parts[0].lower(), parts[1:]


# Обробка помилок
def input_error(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            # Якщо ми самі кидали ValueError з повідомленням — показуємо його
            return str(e) if str(e) else "Invalid arguments. Check command syntax."
        except KeyError:
            return "Contact not found."
        except IndexError:
            return "Enter the argument for the command."
    return wrapper


# Класи для роботи з контактами

class Field:
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)


class Name(Field):
    pass


class Phone(Field):
    def __init__(self, value: str):
        v = str(value)
        # Валідація: тільки цифри і довжина 10
        if not (v.isdigit() and len(v) == 10):
            raise ValueError("Phone must contain exactly 10 digits.")
        super().__init__(v)


class Birthday(Field):
    def __init__(self, value: str):
        try:
            # Перевірка формату DD.MM.YYYY і конвертація в date
            dt = datetime.strptime(value, "%d.%m.%Y").date()
        except ValueError:
            raise ValueError("Invalid date format. Use DD.MM.YYYY")
        super().__init__(dt)

    def __str__(self):
        return self.value.strftime("%d.%m.%Y")


class Record:
    def __init__(self, name: str):
        self.name = Name(name)
        self.phones: list[Phone] = []
        self.birthday: Birthday | None = None  # не обов'язково, тільки одне

    def add_phone(self, phone_value: str) -> None:
        self.phones.append(Phone(phone_value))

    def remove_phone(self, phone_value: str) -> bool:
        for p in self.phones:
            if p.value == phone_value:
                self.phones.remove(p)
                return True
        return False

    def edit_phone(self, old_value: str, new_value: str) -> bool:
        for i, p in enumerate(self.phones):
            if p.value == old_value:
                self.phones[i] = Phone(new_value)
                return True
        return False

    def find_phone(self, phone_value: str) -> Phone | None:
        for p in self.phones:
            if p.value == phone_value:
                return p
        return None

    # додавання дня народження
    def add_birthday(self, birthday_str: str) -> None:
        self.birthday = Birthday(birthday_str)

    def __str__(self):
        phones_str = '; '.join(p.value for p in self.phones) if self.phones else "—"
        bday_str = str(self.birthday) if self.birthday else "—"
        return f"Contact name: {self.name.value}, phones: {phones_str}, birthday: {bday_str}"


class AddressBook(UserDict):
    def add_record(self, record: Record) -> None:
        self.data[record.name.value] = record

    def find(self, name: str) -> Record | None:
        return self.data.get(name)

    def delete(self, name: str) -> bool:
        return self.data.pop(name, None) is not None

    # робота з днями народження
    def get_upcoming_birthdays(self) -> list[dict]:
        today = date.today()
        next_week_end = today + timedelta(days=7)

        # сюди складаємо: день_тижня -> [імена]
        bucket: dict[str, list[str]] = {}

        for record in self.data.values():
            if not record.birthday:
                continue

            bday: date = record.birthday.value
            birthday_this_year = bday.replace(year=today.year)

            # якщо в цьому році вже пройшов — переносимо на наступний
            if birthday_this_year < today:
                birthday_this_year = bday.replace(year=today.year + 1)

            # якщо день народження в межах наступних 7 днів
            if today <= birthday_this_year <= next_week_end:
                congrats_day = birthday_this_year

                # перенос привітання з вихідних на понеділок
                if congrats_day.weekday() == 5:   # Saturday
                    congrats_day = congrats_day + timedelta(days=2)
                elif congrats_day.weekday() == 6:  # Sunday
                    congrats_day = congrats_day + timedelta(days=1)

                day_name = congrats_day.strftime("%A")
                bucket.setdefault(day_name, []).append(record.name.value)

        # формуємо впорядкований список тільки тих днів,
        # де є іменинники, у порядку від сьогодні на 7 днів
        ordered: list[dict[str, list[str]]] = []
        for i in range(7):
            d = (today + timedelta(days=i)).strftime("%A")
            if d in bucket:
                ordered.append({d: sorted(bucket[d])})

        return ordered


# ---------- Команди бота ----------

@input_error
def add_contact(args, book: AddressBook):
    name, phone, *_ = args
    record = book.find(name)
    message = "Contact updated."
    if record is None:
        record = Record(name)
        book.add_record(record)
        message = "Contact added."
    if phone:
        record.add_phone(phone)
    return message


@input_error
def cmd_change(args, book: AddressBook):
    name, old_phone, new_phone = args
    rec = book.find(name)
    if rec is None:
        raise KeyError
    if not rec.edit_phone(old_phone, new_phone):
        return "Phone not found for this contact."
    return "Contact updated."


@input_error
def cmd_phone(args, book: AddressBook):
    name = args[0]
    rec = book.find(name)
    if rec is None:
        raise KeyError
    return '; '.join(p.value for p in rec.phones) if rec.phones else "No phones saved."


@input_error
def cmd_all(args, book: AddressBook):
    if not book.data:
        return "No contacts saved."
    return "\n".join(str(record) for record in book.data.values())


@input_error
def add_birthday(args, book: AddressBook):
    # add-birthday [name] [DD.MM.YYYY]
    name, bday_str, *_ = args
    rec = book.find(name)
    if rec is None:
        # дозволяємо створювати новий контакт одразу з днем народження
        rec = Record(name)
        book.add_record(rec)
    rec.add_birthday(bday_str)
    return "Birthday set."


@input_error
def show_birthday(args, book: AddressBook):
    # show-birthday [name]
    name = args[0]
    rec = book.find(name)
    if rec is None:
        raise KeyError
    return str(rec.birthday) if rec.birthday else "No birthday saved."


@input_error
def birthdays(args, book: AddressBook):
    # birthdays
    upcoming = book.get_upcoming_birthdays()
    if not upcoming:
        return "No upcoming birthdays within the next 7 days."
    lines = []
    for item in upcoming:
        for day, names in item.items():
            lines.append(f"{day}: {', '.join(names)}")
    return "\n".join(lines)


def main():
    book = AddressBook()
    print("Welcome to the assistant bot!")
    while True:
        user_input = input("Enter a command: ")
        command, args = parse_input(user_input)

        if command in ("close", "exit"):
            print("Good bye!")
            break

        elif command == "hello":
            print("How can I help you?")

        elif command == "add":
            print(add_contact(args, book))

        elif command == "change":
            print(cmd_change(args, book))

        elif command == "phone":
            print(cmd_phone(args, book))

        elif command == "all":
            print(cmd_all(args, book))

        elif command == "add-birthday":
            print(add_birthday(args, book))

        elif command == "show-birthday":
            print(show_birthday(args, book))

        elif command == "birthdays":
            print(birthdays(args, book))

        else:
            print("Invalid command.")


if __name__ == "__main__":
    main()
