import re
import asyncio
import os

from receptorctl.socket_interface import ReceptorControl

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reporter.settings')
django.setup()

from reporter.models import WorkUnit, OutputChunk  # NOQA


path = './receptor.sock'

receptor_ctl = ReceptorControl(path)

# Look at current work, clear it out
work_list = receptor_ctl.simple_command('work list')
for unit_id in work_list.keys():
    print(f'Deleting existing work unit {unit_id}')
    receptor_ctl.simple_command(f"work release {unit_id}")
print('')


# Django work unit objects for reference by methods when saving output
work_unit_objects = {}


# submit new work
unit_ids = []
for i in range(3):
    result = receptor_ctl.submit_work(worktype='work1', node='awx_1', payload='')
    unit_id = result['unitid']
    unit_ids.append(unit_id)
    wu = WorkUnit.objects.create(unit_id=unit_id)
    work_unit_objects[unit_id] = wu

receptor_ctl.close()


chunks = []


'''
Everything after this point is async stuff
Key points of this implementation
 - receptorctl is bypassed
 - we do async socket reads, saving to memory
 - periodically flush, saving buffer to database
'''


async def record_output(reader, unit_id):
    """Read messages from the reader and save them in the chunks list"""
    counter = 0
    while True:
        # Analog to ansible-runner Processor main loop... but async
        data = await reader.readline()
        if not data:
            break

        message = data.decode().strip()
        print(f'Received from unit_id={unit_id} message={message}')
        chunks.append(OutputChunk(work_unit=work_unit_objects[unit_id], counter=counter, stdout=message))
        counter += 1


async def monitor_work_unit(unit_id):
    """
    Establishes new async connection, handshakes, requests output
    then starts capturing output
    """
    # Open a new connection to receptor sock, analog to get_work_results
    # https://github.com/ansible/receptor/issues/790
    reader, writer = await asyncio.open_unix_connection(path=path)

    # handshake
    data = await reader.readline()
    text = data.decode().strip()  # readstr
    print(f'receptor first message: {text}')
    m = re.compile("Receptor Control, node (.+)").fullmatch(text)
    print(m)  # also from get_work_results for ValueError, TODO I guess?

    writer.write(f"work results {unit_id} {0}\n".encode())  # writestr
    await writer.drain()

    data = await reader.readline()
    text = data.decode().strip()  # readstr
    print(f'receptor second message: {text}')
    m = re.compile("Streaming results for work unit (.+)").fullmatch(text)
    print(m)

    # Start reading work unit output
    await record_output(reader, unit_id)

    # Close the writer, should we close the reader? Not sure
    writer.close()
    await writer.wait_closed()


# NOTE: consider alternative - axe periodic_flush, wrap readline in wait_for
# await asyncio.wait_for(reader.readline(), timeout=5)
# best depends on how many jobs are running and output frequency


async def periodic_flush():
    """Periodically save the chunks list to the database"""
    dead_count = 0
    while True:
        global chunks
        print(f'Going to save chunks len={len(chunks)}')
        await OutputChunk.objects.abulk_create(chunks)
        chunks = []
        await asyncio.sleep(0.25)
        if not chunks:
            dead_count += 1
        if dead_count > 10:
            break


async def main():
    tasks = []
    for unit_id in unit_ids:
        task = asyncio.create_task(monitor_work_unit(unit_id))
        tasks.append(task)

    task = asyncio.create_task(periodic_flush())
    tasks.append(task)

    await asyncio.gather(*tasks)


asyncio.run(main())
