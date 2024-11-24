# The global text input directory
INPUT_DIR = 'text'
OUTPUT_DIR = 'json'

# creature patterns and lists
CREATURE_SUB_DIR_NAME = 'bestiary'
CREATURE = f'{INPUT_DIR}/{CREATURE_SUB_DIR_NAME}/{{creature}}.txt'  # a single creature pattern
CREATURE_NAMES = glob_wildcards(CREATURE).creature   # all creature names
ALL_CREATURES = expand(CREATURE, creature=CREATURE_NAMES)  # all input creature files
CREATURE_OUTPUT = f'{OUTPUT_DIR}/{CREATURE_SUB_DIR_NAME}/{{creature}}.json' # a single output creature pattern
ALL_CREATURE_OUTPUTS = expand(CREATURE_OUTPUT, creature=CREATURE_NAMES)

# One target to build them all, and in the darkness build them
rule all:
    input: ALL_CREATURE_OUTPUTS
    default_target: True

rule clean:
    shell: 'rm -rf json/'

# pattern rule to build a single creature from text
rule creature:
    input: CREATURE
    output: CREATURE_OUTPUT
    run: 
        # Yes, it's not actually running anything yet. 
        # For now, just copy the input to the output as a fake process
        import shutil
        print(f'Processing {input} --> {output}')
        shutil.copy(str(input), str(output))

# just for debugging
rule echo:
    run: 
        print(CREATURE)
        print(CREATURE_NAMES)
        print(ALL_CREATURES)
        print(CREATURE_OUTPUT)
        print(ALL_CREATURE_OUTPUTS)

