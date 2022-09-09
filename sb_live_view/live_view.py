import sys
import signal
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import seabreeze.spectrometers


class SpectrometerLiveView:

    def __init__(self):

        self.spectrometer = seabreeze.spectrometers.Spectrometer.from_first_available()
        self.spectrometer.integration_time_micros(20000)
        self.wavelengths = self.spectrometer.wavelengths()
        self.count = 0

        self.fig, self.ax = plt.subplots(1,1)
        self.line, = self.ax.plot([],[])
        
        self.ax.set_xlim(self.wavelengths.min(), self.wavelengths.max()) 
        self.ax.set_ylim(0, 1000) 
        self.ax.set_xlabel('wavelength (nm)')
        self.ax.set_ylabel('intensity')
        self.ax.grid(True)

        self.sigint = False
        signal.signal(signal.SIGINT, self.sigint_handler)

    def update(self, frame):
        if self.sigint:
            print('googbye')
            exit(0)
        self.count += 1
        intensities = self.spectrometer.intensities()
        self.line.set_data(self.wavelengths, intensities)
        return (self.line,)

    def sigint_handler(self, signum, frame):
        self.sigint = True

    def run(self):
        animation = FuncAnimation(self.fig, self.update, interval=1)
        plt.show()


def main():
    live_view = SpectrometerLiveView()
    live_view.run()


# ----------------------------------------------------------------------------------------
if __name__ == '__main__':
    main()
