from repeatedtimer import RepeatedTimer

class AsyncClient(object):
	def __init__(self, queue):
		self.queue = queue
		self.rt = RepeatedTimer(5, self.readDataFrame)

	def __del__(self):
		self.rt.stop()

	def start(self):
		self.rt.start()

	def stop(self):
		self.rt.stop()

	def readDataFrame(self):
		"""
		Read in a snapshot of all the data this AsyncClient is setup to
		process.
		"""
		raise NotImplementedError("Should have implemented this")
