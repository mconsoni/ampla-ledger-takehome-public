from datetime import date, datetime, timedelta
from math import floor


class Advance:
	"""
	Class used to represent an Advance

	Attributes:
		creation_date
		initial_amount
		remaining_amount: amount that need to be paid for the advance to be paid off
		daily_interest_rate
		last_interest_payment_date: date for the last time interest were paid
	"""

	def __init__(self, _creation_date, amount, daily_interest_rate, remaining_amount=None):
		"""
		Parameters:
			_creation_date: date formatted as ISO string
			amount: float
			daily_interest_rate: float
			remaining_amount: float, optional
				Amount of the advance that has to be repaid
		"""
		creation_date = date.fromisoformat(_creation_date)
		self.creation_date = creation_date
		self.initial_amount = amount
		self.remaining_amount = remaining_amount if remaining_amount is not None else amount
		self.daily_interest_rate = daily_interest_rate
		self.last_interest_payment_date = creation_date

	def __days_from_last_interest_payment(self, to_date):
		"""
		Calculates the days between `last_interest_payment_day` and `to_date`
		Parameters:
			to_date: date formatted as ISO string
		"""
		_to_date = date.fromisoformat(to_date)
		if _to_date <= self.last_interest_payment_date:
			return 0
		return (_to_date - self.last_interest_payment_date).days

	def interest_payable_balance(self, to_date):
		"""
		Calculates the interest accrued until `to_date`
		Parameters:
			to_date: date formatted as ISO string
		"""
		days = self.__days_from_last_interest_payment(to_date)
		return days * self.interest_by_day()

	def interest_by_day(self):
		return self.remaining_amount * self.daily_interest_rate

	def pay_capital(self, amount):
		"""
		Reduce the remaining_amount

		Parameters:
			amount: float

		Returns:
			float: amount not used to pay off the Advance
		"""
		self.remaining_amount -= amount
		if self.remaining_amount < 0:
			rest = -self.remaining_amount
			self.remaining_amount = 0
			return rest
		return 0

	def pay_interest(self, amount, payment_date):
		"""
		Pay interest of the Advance

		There are two options:
			- The amount is enough to pay the total interest
				* `last_interest_payment_date` is set to `payment_date`
			- The amount is NOT enough to pay the total interest
				* I assume that only one full day's interest can be paid.
				* The number of days of interest covered by the payment is calculated
					and added to `last_interest_payment_date`.
				* The rest is calculated by subtracting the full days interest to amount

		Parameters:
			amount: float
			payment_date: date formatted as ISO string

		Returns:
			tuple (rest: float, interest_paid: float)
				rest: amount not used
				interest_paid: amount paid
		"""
		interest = self.interest_payable_balance(payment_date)
		if amount >= interest:
			self.last_interest_payment_date = date.fromisoformat(payment_date)
			return amount - interest, interest
		else:
			interest_by_day = self.interest_by_day()
			interest_paid_in_days = floor(amount / interest_by_day)
			self.last_interest_payment_date += timedelta(days=interest_paid_in_days)
			interest_amount = interest_paid_in_days * interest_by_day
			return amount - interest_amount, interest_amount

	def is_close(self):
		return self.remaining_amount == 0


class Payment:
	"""
	Class used to represent a Payment

	Attributes:
		creation_date
		amount
	"""
	def __init__(self, creation_date, amount):
		self.creation_date = creation_date
		self.amount = amount


class Balance:
	"""
	Class used to represent the Balance of a Customer

	Attributes:
		advances: list(Advance)
			List of advances given to the customer
		payments: list(Payment)
			List of payments made by the customer
		interest_paid: float
			Amount of interest paid by the customer
		daily_interest_rate: float
		balance: float
			Available amount for immediately repayment

	Properties:
		unpaid_advances: list(Advance)
			List of not paid off advances

	Methods:
		add_advance(advance_date, amount, daily_interest_rate=None)
		add_payment(payment_date, amount)
		advances_balance()
		interest_payable_balance(to_date)
	"""
	def __init__(self, daily_interest_rate, balance=0):
		"""
		Parameters:
			daily_interest_rate: float
			balance: float, optional
				Available amount for immediately repayment
				Default: 0
		"""
		self.advances = []
		self.__unpaid_advances = []
		self.payments = []
		self.interest_paid = 0
		self.daily_interest_rate = daily_interest_rate
		self.balance = balance

	def add_advance(self, advance_date, amount, daily_interest_rate=None):
		"""
		Add an advance to the balance

		Parameters:
			advance_date: date formatted as ISO string
			amount: float
			daily_interest_rate: float, optional
				Each advance can have its own daily interest rate
				Default: Balance's daily interest rate
		"""
		if daily_interest_rate is None:
			daily_interest_rate = self.daily_interest_rate
		# Use the available amount for immediately repayment
		remaining_amount = amount
		if self.balance > remaining_amount:
			self.balance -= remaining_amount
			remaining_amount = 0
		else:
			remaining_amount -= self.balance
			self.balance = 0
		advance = Advance(advance_date, amount, daily_interest_rate, remaining_amount)
		self.advances.append(advance)
		self.__unpaid_advances.append(advance)

	def add_payment(self, payment_date, amount):
		"""
		Add a payment to the balance

		Parameters:
			payment_date: date formatted as ISO string
			amount: float
		"""
		self.payments.append(Payment(payment_date, amount))
		self.balance += amount
		self.__pay_interest(payment_date)
		self.__pay_capital()

	def __pay_capital(self):
		"""
		Use the amount available in self.balance to reduce the remaining amount of the Advances and update self.balance
		"""
		for advance in self.unpaid_advances():
			if self.balance == 0:
				break
			self.balance = advance.pay_capital(self.balance)

	def __pay_interest(self, payment_date=datetime.now().date().isoformat()):
		"""
		Use the amount available in self.balance to pay the interest of the advances and update self.balance

		Parameters:
			payment_date: date formatted as ISO string, optional
				Default: current date
		"""
		for advance in self.unpaid_advances():
			if self.balance == 0:
				break
			(rest, interest_paid) = advance.pay_interest(self.balance, payment_date)
			self.balance = rest
			self.interest_paid += interest_paid

	def unpaid_advances(self):
		"""
		Generator to iterate the list of unpaid advances
		"""
		i = 0
		length = len(self.__unpaid_advances)
		while i < length:
			advance = self.__unpaid_advances[i]
			if not advance.is_close():
				yield advance
				# Every time an unpaid advance is used check if it was closed for removing it from the list.
				if advance.is_close():
					self.__unpaid_advances.remove(advance)
					i -= 1
					length -= 1
			i += 1

	def advances_balance(self):
		"""
		Calculates the mount owed by the customer

		Returns: float
		"""
		return sum([a.remaining_amount for a in self.unpaid_advances()])

	def interest_payable_balance(self, to_date):
		"""
		Calculate the total interest owed by the customer until `to_date`
		`to_date` is included in the calculation

		Parameters:
			to_date: date formatted as ISO string

		Returns: float
		"""
		# Use the next day to include to_date in the calculation
		_to_date = (date.fromisoformat(to_date) + timedelta(days=1)).isoformat()
		return sum([a.interest_payable_balance(_to_date) for a in self.unpaid_advances()])
