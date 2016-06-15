class AsyncClient:
	def __init__(self, queue):
		this.queue = queue
		this.rt = RepeatedTimer(1, readDataFrame, this)

	def __del__(self):
		this.rt.stop()

	def readDataFrame(self):
		"""
		Read in a snapshot of all the data this AsyncClient is setup to
		process.
		"""
		return