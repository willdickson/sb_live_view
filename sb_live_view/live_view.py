import sys
import signal
import collections
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import seabreeze.spectrometers

mpl.rcParams['keymap.save'].remove('s')
mpl.rcParams['keymap.home'].remove('h')

if 0:
    for k, v in mpl.rcParams.items():
        if 'keymap' in k:
            print(k,v)


class SpectrometerLiveView: 

    INTENSITY_MODE = 0
    ABSORBANCE_MODE = 1 

    YRANGE_INTENSITY_DEFAULT = 4000
    YRANGE_INTENSITY_STEP = 500
    YRANGE_INTENSITY_MIN = 500

    YRANGE_ABSORBANCE_DEFAULT = 1.1 
    YRANGE_ABSORBANCE_STEP = 0.1 
    YRANGE_ABSORBANCE_MIN = 0.1 

    INTEG_WIN_DEFAULT = 4000
    INTEG_WIN_STEP = 500 
    INTEG_WIN_MIN = 3000

    LIVEVIEW_LINE_COLOR = 'b'
    BLANKING_LINE_COLOR = 'g'

    MODE_TO_YLABEL = {
            INTENSITY_MODE:  'Intensity', 
            ABSORBANCE_MODE: 'Absorbance',
            }
    
    MODE_TO_YRANGE_DEFAULT = {
            INTENSITY_MODE:  YRANGE_INTENSITY_DEFAULT, 
            ABSORBANCE_MODE: YRANGE_ABSORBANCE_DEFAULT, 
            }
            

    def __init__(self):

        self.spectrometer = seabreeze.spectrometers.Spectrometer.from_first_available()
        self.integ_window = self.INTEG_WIN_DEFAULT
        self.spectrometer.integration_time_micros(self.integ_window)
        self.wavelengths = self.spectrometer.wavelengths()
        self.blanking_intensities = None
        self.display_mode = self.INTENSITY_MODE

        self.fig, self.ax = plt.subplots(1,1)
        self.liveview_line, = self.ax.plot([],[], self.LIVEVIEW_LINE_COLOR)
        self.blanking_line, = self.ax.plot([],[], self.BLANKING_LINE_COLOR)
        
        self.ax.set_xlim(self.wavelengths.min(), self.wavelengths.max()) 
        self.ax.set_ylim(0, self.YRANGE_INTENSITY_DEFAULT) 
        self.ax.set_xlabel('Wavelength (nm)')
        self.ax.set_ylabel(self.MODE_TO_YLABEL[self.display_mode])
        self.ax.grid(True)

        self.sigint = False
        signal.signal(signal.SIGINT, self.sigint_handler)

        self.event_key_to_callback = collections.OrderedDict([
                ('s'    , self.save), 
                ('b'    , self.blank),
                ('c'    , self.clear_blank),
                ('up'   , self.increase_y_range),
                ('down' , self.decrease_y_range) ,
                ('i'    , self.set_mode_to_intensity) ,
                ('a'    , self.set_mode_to_absorbance),
                ('.'    , self.increase_integ_window),
                (','    , self.decrease_integ_window) ,
                ('h'    , self.print_help),
                ])

        self.event_key_to_doc = collections.OrderedDict([
                ('s'    ,   'save figure'),
                ('b'    ,   'acquire blanking data'),
                ('c'    ,   'clear blanking data'),
                ('up'   ,   'increase plot y axis range'),
                ('down' ,   'decrease plot y axis range'),
                ('i'    ,   'display intensity vs wavelength'),
                ('a'    ,   'display absorbance vs wavelength'),
                ('<'    ,   'increase integration window') ,
                ('>'    ,   'decrease integration window') ,
                ('h'    ,   'print help message') ,
                ('q'    ,   'quit'),
                ])

        self.fig.canvas.mpl_connect('key_press_event', self.on_key_press)

        self.print_help()


    def on_key_press(self, event):
        """
        Switchyard for handling key press events
        """
        try:
            self.event_key_to_callback[event.key]()
        except KeyError:
            print(f'KeyError: {event.key}')

    def save(self):
        """
        Save figure and associated data.
        """
        print('saving data')

    def blank(self):
        """
        Save blanking intensities for use during absorbance mode.
        """
        _, self.blanking_intensities  = self.liveview_line.get_data()
        print('blanking data acquired')

    def clear_blank(self):
        """
        Clear blanking intentities
        """
        self.blanking_intensities = None
        print('clearing blanking data')

    def increase_y_range(self):
        """
        Increase the live view plot's y range by one step size.
        """
        y_min, y_max = self.ax.get_ylim()
        y_max_new = y_max + self.YRANGE_INTENSITY_STEP
        self.ax.set_ylim(y_min, y_max_new)
        print(f'y range = {y_max_new}')

    def decrease_y_range(self):
        """
        Decrease the live view plot's y range by one step size until
        the minimum size is reached. 
        """
        y_min, y_max = self.ax.get_ylim()
        y_max_new = max(y_max - self.YRANGE_INTENSITY_STEP, self.YRANGE_INTENSITY_MIN)
        self.ax.set_ylim(y_min, y_max_new)
        print(f'y range = {y_max_new}')

    def set_mode_to_intensity(self):
        """
        Set display mode to intensity
        """
        self.display_mode = self.INTENSITY_MODE
        self.ax.set_ylim(0, self.YRANGE_INTENSITY_DEFAULT) 
        self.ax.set_ylabel(self.MODE_TO_YLABEL[self.display_mode])

    def set_mode_to_absorbance(self):
        """
        Set mode to display absorbance
        """
        if self.blanking_intensities is None:
            print('unable to display absorbance - no blanking data')
        else:
            self.display_mode = self.ABSORBANCE_MODE
            self.ax.set_ylim(0, self.YRANGE_ABSORBANCE_DEFAULT) 
            self.ax.set_ylabel(self.MODE_TO_YLABEL[self.display_mode])

    def print_help(self):
        """
        Prints a help message displaying the hot keys and describing
        their associated commands.
        """
        print()
        print('commands')
        print('------------------------------------------')
        for k, v in self.event_key_to_doc.items():
            print(f'{k} \t =  {v}')
        print('------------------------------------------')
        print()

    def increase_integ_window(self):
        """
        Increase the spectrometer integration window by one step
        """
        self.integ_window += self.INTEG_WIN_STEP
        self.spectrometer.integration_time_micros(self.integ_window)
        print(f'integration window = {self.integ_window}')
        

    def decrease_integ_window(self):
        """
        Decrease the spectrometer integration window by one step
        """
        self.integ_window -= self.INTEG_WIN_STEP
        self.integ_window = max(self.integ_window, self.INTEG_WIN_MIN)
        self.spectrometer.integration_time_micros(self.integ_window)
        print(f'integration window = {self.integ_window}')

    def update(self, frame):
        """
        Read intensities from sensor and update live plot
        """
        if self.sigint:
            print('googbye')
            exit(0)

        update_list = []
        intensities = self.spectrometer.intensities()
        self.liveview_line.set_data(self.wavelengths, intensities)
        update_list.append(self.liveview_line)

        if self.blanking_intensities is not None:
            self.blanking_line.set_data(self.wavelengths, self.blanking_intensities)
            update_list.append(self.blanking_line)
        else:
            self.blanking_line.set_data(self.wavelengths, self.blanking_intensities)
            update_list.append(self.blanking_line)

        return update_list 

    def sigint_handler(self, signum, frame):
        """
        Handle SIGINT in order to quit properly
        """
        self.sigint = True

    def run(self):
        """
        Start the live view
        """
        animation = FuncAnimation(self.fig, self.update, interval=1)
        plt.show()


def main():
    live_view = SpectrometerLiveView()
    live_view.run()


# ----------------------------------------------------------------------------------------
if __name__ == '__main__':
    main()
