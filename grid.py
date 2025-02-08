import random
import time
import threading
import pygame
import sys
import math

# Default values of signal timers
defaultGreen = {0: 10, 1: 10, 2: 10, 3: 10}  # Default green time for each signal
defaultRed = 150
defaultYellow = 5

# Define the grid size (2x2)
GRID_ROWS = 2
GRID_COLS = 2

# Initialize intersections
intersections = [[{
    'signals': [],
    'vehicles': {'right': {0: [], 1: [], 2: [], 'crossed': 0},
                 'down': {0: [], 1: [], 2: [], 'crossed': 0},
                 'left': {0: [], 1: [], 2: [], 'crossed': 0},
                 'up': {0: [], 1: [], 2: [], 'crossed': 0}},
    'currentGreen': 0,
    'nextGreen': 1,
    'currentYellow': 0
} for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]

noOfSignals = 4
speeds = {'car': 2.25, 'bus': 1.5, 'truck': 1.125, 'bike': 2, 'ambulance': 2.15}  # Reduced speeds for resized intersections

# Coordinates of vehicles' start (scaled down for resized intersections)
x = {'right': [0, 0, 0], 'down': [377, 363, 348], 'left': [700, 700, 700], 'up': [301, 313, 328]}
y = {'right': [174, 185, 199], 'down': [0, 0, 0], 'left': [249, 233, 218], 'up': [400, 400, 400]}

vehicleTypes = {0: 'car', 1: 'bus', 2: 'truck', 3: 'bike', 4: 'ambulance'}
directionNumbers = {0: 'right', 1: 'down', 2: 'left', 3: 'up'}
weights = {'car': 2, 'bus': 4, 'truck': 6, 'bike': 1, 'ambulance': 1000}

# Coordinates of signal image, timer, and vehicle count (scaled down for resized intersections)
signalCoods = [(265, 50), (410, 50), (410, 260), (265, 260)]
signalTimerCoods = [(270,25), (415, 25), (415, 240), (270, 240)]

# Coordinates of stop lines (scaled down for resized intersections)
stopLines = {'right': 295, 'down': 165, 'left': 400, 'up': 267}
defaultStop = {'right': 290, 'down': 160, 'left': 405, 'up': 272}

# Gap between vehicles
stoppingGap = 7  # Reduced stopping gap for resized intersections
movingGap = 7  # Reduced moving gap for resized intersections

pygame.init()
simulation = pygame.sprite.Group()


class TrafficSignal:
    def __init__(self, red, yellow, green):
        self.red = red
        self.yellow = yellow
        self.green = green
        self.signalText = ""


class Vehicle(pygame.sprite.Sprite):
    def __init__(self, lane, vehicleClass, direction_number, direction, intersection):
        pygame.sprite.Sprite.__init__(self)
        self.lane = lane
        self.vehicleClass = vehicleClass
        self.speed = speeds[vehicleClass]
        self.direction_number = direction_number
        self.direction = direction
        self.intersection = intersection  # Track which intersection the vehicle is in
        self.x = x[direction][lane] + intersection[1] * 700  # Adjust x-coordinate for intersection
        self.y = y[direction][lane] + intersection[0] * 400  # Adjust y-coordinate for intersection
        self.crossed = 0
        self.target_intersection = None  # Track the next intersection the vehicle is heading to

        # Add vehicle to the current intersection's vehicle queue
        intersections[self.intersection[0]][self.intersection[1]]['vehicles'][direction][lane].append(self)
        self.index = len(intersections[self.intersection[0]][self.intersection[1]]['vehicles'][direction][lane]) - 1

        # Load vehicle image
        path = "images/" + direction + "/" + vehicleClass + ".png"
        self.image = pygame.image.load(path)

        # Set initial stop position
        if (len(intersections[self.intersection[0]][self.intersection[1]]['vehicles'][direction][lane]) > 1 and
                intersections[self.intersection[0]][self.intersection[1]]['vehicles'][direction][lane][
                    self.index - 1].crossed == 0):
            if direction == 'right':
                self.stop = intersections[self.intersection[0]][self.intersection[1]]['vehicles'][direction][lane][
                                self.index - 1].stop - self.image.get_rect().width - stoppingGap
            elif direction == 'left':
                self.stop = intersections[self.intersection[0]][self.intersection[1]]['vehicles'][direction][lane][
                                self.index - 1].stop + self.image.get_rect().width + stoppingGap
            elif direction == 'down':
                self.stop = intersections[self.intersection[0]][self.intersection[1]]['vehicles'][direction][lane][
                                self.index - 1].stop - self.image.get_rect().height - stoppingGap
            elif direction == 'up':
                self.stop = intersections[self.intersection[0]][self.intersection[1]]['vehicles'][direction][lane][
                                self.index - 1].stop + self.image.get_rect().height + stoppingGap
        else:
            self.stop = defaultStop[direction] + intersection[1] * 700 if direction in ['right', 'left'] else defaultStop[direction] + intersection[0] * 400

        # Update starting coordinates for the next vehicle
        if direction == 'right':
            temp = self.image.get_rect().width + stoppingGap
            x[direction][lane] -= temp
        elif direction == 'left':
            temp = self.image.get_rect().width + stoppingGap
            x[direction][lane] += temp
        elif direction == 'down':
            temp = self.image.get_rect().height + stoppingGap
            y[direction][lane] -= temp
        elif direction == 'up':
            temp = self.image.get_rect().height + stoppingGap
            y[direction][lane] += temp

        simulation.add(self)

    def move(self):
        # Move the vehicle within the current intersection
        if self.direction == 'right':
            if self.crossed == 0 and self.x + self.image.get_rect().width > stopLines[self.direction] + self.intersection[1] * 700:
                self.crossed = 1
            if ((self.x + self.image.get_rect().width <= self.stop or self.crossed == 1 or (
                    intersections[self.intersection[0]][self.intersection[1]]['currentGreen'] == 0 and
                    intersections[self.intersection[0]][self.intersection[1]]['currentYellow'] == 0)) and (
                    self.index == 0 or self.x + self.image.get_rect().width < (
                    intersections[self.intersection[0]][self.intersection[1]]['vehicles'][self.direction][self.lane][
                        self.index - 1].x - movingGap))):
                self.x += self.speed
        # Add similar logic for other directions (left, down, up)

        # Check if the vehicle has exited the current intersection
        if self.crossed == 1 and self.target_intersection is not None:
            # Move the vehicle to the target intersection
            self.intersection = self.target_intersection
            self.crossed = 0
            self.target_intersection = None


def countVehicles(intersection):
    counts = [0, 0, 0, 0]  # Total vehicles per direction
    noOfCars = [0, 0, 0, 0]
    noOfBuses = [0, 0, 0, 0]
    noOfTrucks = [0, 0, 0, 0]
    noOfBikes = [0, 0, 0, 0]
    noOfAmbulances = [0, 0, 0, 0]

    for i in range(noOfSignals):
        direction = directionNumbers[i]
        for lane in [0, 1, 2]:
            for vehicle in intersection['vehicles'][direction][lane]:
                if not vehicle.crossed:
                    if hasattr(vehicle, 'image'):  # Check if the vehicle has the 'image' attribute
                        rect = vehicle.image.get_rect()
                        # Check if the vehicle is an ambulance
                        if vehicle.vehicleClass == 'ambulance':
                            counts[i] += 1
                            noOfAmbulances[i] += 1
                        else:
                            # For other vehicles, count only if they are within a certain distance from the stop line
                            if direction == 'right':
                                if (vehicle.x + rect.width > stopLines[direction] + vehicle.intersection[1] * 700 - 165 and vehicle.x + rect.width < stopLines[direction] + vehicle.intersection[1] * 700):
                                    counts[i] += 1
                                    if vehicle.vehicleClass == 'car':
                                        noOfCars[i] += 1
                                    elif vehicle.vehicleClass == 'bus':
                                        noOfBuses[i] += 1
                                    elif vehicle.vehicleClass == 'truck':
                                        noOfTrucks[i] += 1
                                    elif vehicle.vehicleClass == 'bike':
                                        noOfBikes[i] += 1
                            elif direction == 'left':
                                if (vehicle.x < stopLines[direction] + vehicle.intersection[1] * 700 + 165 and vehicle.x > stopLines[direction] + vehicle.intersection[1] * 700):
                                    counts[i] += 1
                                    if vehicle.vehicleClass == 'car':
                                        noOfCars[i] += 1
                                    elif vehicle.vehicleClass == 'bus':
                                        noOfBuses[i] += 1
                                    elif vehicle.vehicleClass == 'truck':
                                        noOfTrucks[i] += 1
                                    elif vehicle.vehicleClass == 'bike':
                                        noOfBikes[i] += 1
                            elif direction == 'down':
                                if (vehicle.y + rect.height > stopLines[direction] + vehicle.intersection[0] * 400 - 165 and vehicle.y + rect.height < stopLines[direction] + vehicle.intersection[0] * 400):
                                    counts[i] += 1
                                    if vehicle.vehicleClass == 'car':
                                        noOfCars[i] += 1
                                    elif vehicle.vehicleClass == 'bus':
                                        noOfBuses[i] += 1
                                    elif vehicle.vehicleClass == 'truck':
                                        noOfTrucks[i] += 1
                                    elif vehicle.vehicleClass == 'bike':
                                        noOfBikes[i] += 1
                            elif direction == 'up':
                                if (vehicle.y < stopLines[direction] + vehicle.intersection[0] * 400 + 125 and vehicle.y > stopLines[direction] + vehicle.intersection[0] * 400):
                                    counts[i] += 1
                                    if vehicle.vehicleClass == 'car':
                                        noOfCars[i] += 1
                                    elif vehicle.vehicleClass == 'bus':
                                        noOfBuses[i] += 1
                                    elif vehicle.vehicleClass == 'truck':
                                        noOfTrucks[i] += 1
                                    elif vehicle.vehicleClass == 'bike':
                                        noOfBikes[i] += 1

    print(f"Vehicle Counts: {counts} (Cars: {noOfCars}, Buses: {noOfBuses}, Trucks: {noOfTrucks}, Bikes: {noOfBikes}, Ambulances:{noOfAmbulances})")
    weighted = [0, 0, 0, 0]
    for i in range(4):
        weighted[i] = noOfCars[i] * weights['car'] + noOfBikes[i] * weights['bike'] + noOfBuses[i] * weights['bus'] + noOfTrucks[i] * weights['truck'] + noOfAmbulances[i] * weights['ambulance']
    return counts, noOfCars, noOfBuses, noOfTrucks, noOfBikes, noOfAmbulances, weighted


def initialize():
    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            ts1 = TrafficSignal(0, defaultYellow, defaultGreen[0])
            intersections[row][col]['signals'].append(ts1)
            ts2 = TrafficSignal(ts1.red + ts1.yellow + ts1.green, defaultYellow, defaultGreen[1])
            intersections[row][col]['signals'].append(ts2)
            ts3 = TrafficSignal(defaultRed, defaultYellow, defaultGreen[2])
            intersections[row][col]['signals'].append(ts3)
            ts4 = TrafficSignal(defaultRed, defaultYellow, defaultGreen[3])
            intersections[row][col]['signals'].append(ts4)
    repeat()


def repeat():
    while True:
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                intersection = intersections[row][col]
                counts, noOfCars, noOfBuses, noOfTrucks, noOfBikes, noOfAmbulances, weighted = countVehicles(intersection)

                # Check if there is an ambulance in any lane
                ambulance_present = any(noOfAmbulances)
                ambulance_direction = None

                if ambulance_present:
                    # Find the direction with the ambulance
                    for i in range(noOfSignals):
                        if noOfAmbulances[i] > 0:
                            ambulance_direction = i
                            break

                # If an ambulance is present, prioritize its lane
                if ambulance_present:
                    intersection['currentGreen'] = ambulance_direction
                    intersection['signals'][intersection['currentGreen']].green = 5  # Reduced from 10 to 5 seconds
                else:
                    # No ambulance, proceed with normal logic
                    total_vehicles = noOfCars[intersection['currentGreen']] + noOfBuses[intersection['currentGreen']] + noOfTrucks[intersection['currentGreen']] + noOfBikes[intersection['currentGreen']]
                    greenTime = max(weighted)
                    maxIndex = weighted.index(greenTime)
                    greenTime = max(5, min(60, greenTime))  # Minimum 5 seconds, maximum 60 seconds
                    intersection['currentGreen'] = maxIndex
                    intersection['signals'][intersection['currentGreen']].green = math.ceil(greenTime / 3.68)

                # Execute the green signal
                while intersection['signals'][intersection['currentGreen']].green > 0:
                    updateValues(intersection)
                    time.sleep(1)

                # Dynamic yellow signal timing
                if counts[intersection['currentGreen']] > 0:
                    intersection['signals'][intersection['currentGreen']].yellow = max(1, min(3, counts[intersection['currentGreen']] // 5))
                else:
                    intersection['signals'][intersection['currentGreen']].yellow = 0

                intersection['currentYellow'] = 1
                for i in range(0, 3):
                    for vehicle in intersection['vehicles'][directionNumbers[intersection['currentGreen']]][i]:
                        vehicle.stop = defaultStop[directionNumbers[intersection['currentGreen']]] + intersection[1] * 700 if directionNumbers[intersection['currentGreen']] in ['right', 'left'] else defaultStop[directionNumbers[intersection['currentGreen']]] + intersection[0] * 400
                while intersection['signals'][intersection['currentGreen']].yellow > 0:
                    updateValues(intersection)
                    time.sleep(1)
                intersection['currentYellow'] = 0

                # Reset all signal times of current signal to default times
                intersection['signals'][intersection['currentGreen']].green = defaultGreen[intersection['currentGreen']]
                intersection['signals'][intersection['currentGreen']].yellow = defaultYellow
                intersection['signals'][intersection['currentGreen']].red = defaultRed

                intersection['currentGreen'] = intersection['nextGreen']
                intersection['nextGreen'] = (intersection['currentGreen'] + 1) % noOfSignals
                intersection['signals'][intersection['nextGreen']].red = intersection['signals'][intersection['currentGreen']].yellow + intersection['signals'][intersection['currentGreen']].green


def updateValues(intersection):
    for i in range(0, noOfSignals):
        if i == intersection['currentGreen']:
            if intersection['currentYellow'] == 0:
                intersection['signals'][i].green -= 1
            else:
                intersection['signals'][i].yellow -= 1
        else:
            if i == intersection['nextGreen']:
                intersection['signals'][i].red = intersection['signals'][intersection['currentGreen']].yellow + intersection['signals'][intersection['currentGreen']].green
            else:
                intersection['signals'][i].red = max(0, intersection['signals'][i].red - 1)


def generateVehicles():
    while True:
        vehicle_type = random.randint(0, 3)
        if random.randint(0, 10) == 5:
            vehicle_type = 4  # Ambulance
        lane_number = random.randint(1, 2)
        temp = random.randint(0, 99)
        direction_number = 0
        dist = [25, 50, 75, 100]
        if temp < dist[0]:
            direction_number = 0
        elif temp < dist[1]:
            direction_number = 1
        elif temp < dist[2]:
            direction_number = 2
        elif temp < dist[3]:
            direction_number = 3
        intersection = (random.randint(0, GRID_ROWS - 1), random.randint(0, GRID_COLS - 1))
        Vehicle(lane_number, vehicleTypes[vehicle_type], direction_number, directionNumbers[direction_number], intersection)
        time.sleep(1)


class Main:
    thread1 = threading.Thread(name="initialization", target=initialize, args=())  # initialization
    thread1.daemon = True
    thread1.start()

    # Colours
    black = (0, 0, 0)
    white = (255, 255, 255)

    # Screensize
    screenWidth = 1400
    screenHeight = 800
    screenSize = (screenWidth, screenHeight)

    # Setting background image i.e. image of intersection
    background = pygame.image.load('images/intersection_new.jpg')  # Load the merged 2x2 background image
    background = pygame.transform.scale(background, (screenWidth, screenHeight))
    screen = pygame.display.set_mode(screenSize)
    pygame.display.set_caption("SIMULATION")

    # Loading signal images and font
    redSignal = pygame.image.load('images/signals/red.png')
    yellowSignal = pygame.image.load('images/signals/yellow.png')
    greenSignal = pygame.image.load('images/signals/green.png')
    font = pygame.font.Font(None, 30)

    thread2 = threading.Thread(name="generateVehicles", target=generateVehicles, args=())  # Generating vehicles
    thread2.daemon = True
    thread2.start()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()

        screen.blit(background, (0, 0))  # Display the merged 2x2 background image

        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                intersection = intersections[row][col]
                counts, noOfCars, noOfBuses, noOfTrucks, noOfBikes, noOfAmbulances, weighted = countVehicles(intersection)
                for i in range(0, noOfSignals):
                    if i == intersection['currentGreen']:
                        if intersection['currentYellow'] == 1:
                            intersection['signals'][i].signalText = intersection['signals'][i].yellow
                            screen.blit(yellowSignal, (signalCoods[i][0] + col * 700, signalCoods[i][1] + row * 400))
                        else:
                            intersection['signals'][i].signalText = intersection['signals'][i].green
                            screen.blit(greenSignal, (signalCoods[i][0] + col * 700, signalCoods[i][1] + row * 400))
                    else:
                        if intersection['signals'][i].red <= 10:
                            intersection['signals'][i].signalText = intersection['signals'][i].red
                        else:
                            intersection['signals'][i].signalText = "---"
                        screen.blit(redSignal, (signalCoods[i][0] + col * 700, signalCoods[i][1] + row * 400))
                signalTexts = ["", "", "", ""]

                # display signal timer
                for i in range(0, noOfSignals):
                    signalTexts[i] = font.render(str(intersection['signals'][i].signalText), True, white, black)
                    screen.blit(signalTexts[i], (signalTimerCoods[i][0] + col * 700, signalTimerCoods[i][1] + row * 400))

                # display vehicle count beside the signal
                for i in range(0, noOfSignals):
                    countText = font.render(f"Vehicles: {counts[i]}", True, white, black)
                    if i == 0:  # Right signal (top-left corner)
                        screen.blit(countText, (50 + col * 700, 50 + row * 400))  # Top-left corner
                    elif i == 1:  # Down signal (top-right corner)
                        screen.blit(countText, (screenWidth // 2 - 150 + col * 700, 50 + row * 400))  # Top-right corner
                    elif i == 2:  # Left signal (bottom-left corner)
                        screen.blit(countText, (screenWidth // 2 - 150 + col * 700, screenHeight // 2 - 50 + row * 400))  # Bottom-left corner
                    elif i == 3:  # Up signal (bottom-right corner)
                        screen.blit(countText, (50 + col * 700, screenHeight // 2 - 50 + row * 400))  # Bottom-right corner

        # display the vehicles
        for vehicle in simulation:
            screen.blit(vehicle.image, [vehicle.x, vehicle.y])
            vehicle.move()
        pygame.display.update()


Main()
